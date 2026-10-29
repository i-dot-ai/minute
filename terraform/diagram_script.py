"""Regenerate the simple architecture overview: uv run python terraform/diagram_script.py."""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge, Node
from diagrams.aws.compute import ECS
from diagrams.aws.database import Aurora
from diagrams.aws.general import Users
from diagrams.aws.network import ALB
from diagrams.aws.storage import S3
from diagrams.azure.ml import CognitiveServices
from diagrams.gcp.ml import AIPlatform

output = Path(__file__).resolve().parents[1] / "minute_architecture_diagram"
temporal_logo = Path(__file__).resolve().parent / "diagram-assets" / "temporal-logo.png"

with Diagram(
    "",
    filename=str(output),
    outformat="png",
    direction="TB",
    show=False,
    graph_attr={
        "bgcolor": "white",
        "pad": "0.3",
        "nodesep": "0.55",
        "ranksep": "0.5",
        "splines": "spline",
        "newrank": "true",
        "ordering": "out",
    },
    node_attr={"fontsize": "12"},
    edge_attr={"color": "#64748b", "fontsize": "11"},
) as diagram:
    users = Users("User", group="entry")
    with Cluster("Internal Access · managed separately", graph_attr={"bgcolor": "#f0edff"}):
        internal_access = Node(
            "Sign-in\n& identity check",
            shape="box",
            style="rounded,filled",
            fillcolor="white",
            color="#8071c7",
            width="2.0",
            height="1.1",
            labelloc="c",
            group="entry",
        )
    with Cluster("Secure access to Minute · user is logged in", graph_attr={"bgcolor": "#edf7ec"}):
        with Cluster("", graph_attr={"style": "invis"}):
            signed_in_user = Users("Signed-in user", group="entry")
        with Cluster("AWS Cloud · London (eu-west-2)", graph_attr={"bgcolor": "#e5f5fd"}):
            access = ALB("Load balancer\nApp access")
            frontend = ECS("Frontend\nMeeting workspace")
            backend = ECS("Backend\nManages meetings")
            temporal = Node(
                f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
                f'<TR><TD WIDTH="140" HEIGHT="34" FIXEDSIZE="TRUE"><IMG SRC="{temporal_logo}" SCALE="TRUE"/></TD></TR>'
                "<TR><TD>Workflow coordination<BR/>&amp; retries</TD></TR></TABLE>>",
                shape="box",
                style="rounded,filled",
                fillcolor="#e8e5ff",
                color="#8071c7",
                width="2.2",
                height="1.1",
                labelloc="c",
            )
            worker = ECS("Worker\nAudio & minutes")
            audio = S3("Audio files\nS3 storage", group="audio")
            # Route the audio connection below the workflow arrow without adding a visible component.
            audio_route = Node("", shape="point", style="invis", width="0", height="0", group="audio")
            meetings = Aurora("Meetings & minutes\nAurora PostgreSQL")
            workflow_history = Aurora("Workflow history\nTemporal database")

    with Cluster("Azure Cloud"):
        speech = CognitiveServices("Azure Speech\nAudio to text")
    with Cluster("Google Cloud"):
        gemini = AIPlatform("Gemini\nAI summaries")

    with diagram.dot.subgraph() as row:
        row.attr(rank="same")
        for node in [users, internal_access]:
            row.node(node.nodeid)
    with diagram.dot.subgraph() as row:
        row.attr(rank="same")
        for node in [signed_in_user, access, frontend, backend]:
            row.node(node.nodeid)
    with diagram.dot.subgraph() as row:
        row.attr(rank="same")
        for node in [audio, temporal, workflow_history, meetings]:
            row.node(node.nodeid)
    with diagram.dot.subgraph() as row:
        row.attr(rank="same")
        for node in [audio_route, worker, speech, gemini]:
            row.node(node.nodeid)

    users >> internal_access
    internal_access >> Edge(label="Sign-in successful") >> signed_in_user
    signed_in_user >> Edge(weight="100") >> access
    access >> frontend >> backend
    backend >> Edge(label="Start processing") >> temporal
    temporal >> Edge(label="Coordinate work") >> worker
    temporal >> workflow_history
    backend >> meetings
    backend >> Edge(label="Authorise upload") >> audio
    (
        signed_in_user
        >> Edge(label="Authorised audio upload\n(time-limited link)", color="#719a24", constraint="false")
        >> audio
    )
    audio >> Edge(style="invis") >> temporal
    workflow_history >> Edge(style="invis") >> meetings
    audio >> Edge(color="#719a24", arrowhead="none", tailport="s") >> audio_route
    audio_route >> Edge(color="#719a24") >> worker
    worker >> Edge(constraint="false") >> meetings
    worker >> speech
    worker >> gemini
