from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import ECS
from diagrams.aws.general import Users
from diagrams.aws.integration import SimpleNotificationServiceSnsTopic
from diagrams.aws.management import AutoScaling, Cloudwatch, CloudwatchAlarm
from diagrams.aws.network import ELB
from diagrams.aws.security import WAF, Cognito, Guardduty, SecretsManager
from diagrams.aws.storage import S3

graph_attr = {
    "fontsize": "14",
    "bgcolor": "transparent",
    "splines": "ortho",
}

with Diagram(
    "AWS architecture",
    filename="aws_architecture",
    outformat="jpg",
    direction="TB",
    show=False,
    graph_attr=graph_attr,
):
    with Cluster("I.AI dev account"):  # noqa: SIM117
        with Cluster("eu-west-2"):
            with Cluster("VPC"):
                with Cluster("Account wide security"):
                    guard_duty = Guardduty("GuardDuty")
                with Cluster("Private subnet") as private_subnet:
                    waf = WAF("WAF")

                    with Cluster("SNS"):
                        sns_topic = SimpleNotificationServiceSnsTopic("SNS")

                    with Cluster("ECS"):
                        frontend = ECS("Frontend")

                        backend = ECS("Backend")

                    with Cluster("Autoscaling"):
                        usage_scaling_group = AutoScaling("Usage scaling")
                        peaktime_scaling_group = AutoScaling("Peak time scaling")

                    with Cluster("Observability"):
                        cloudwatch_alarms = CloudwatchAlarm("Service monitoring")

                    with Cluster("File storage"):
                        s3 = S3("AWS S3 bucket")

                    with Cluster("Secret storage"):
                        secrets = SecretsManager("AWS secrets manager")

                    with Cluster("App logs/metrics"):
                        cloudwatch = Cloudwatch("CloudWatch logs")

                with Cluster("Public subnet"):
                    alb = ELB("Application load balancer")
                    cognito = Cognito("Cognito")

    users = Users("User")

    users >> cognito

    cognito >> alb >> waf >> backend
    backend >> s3
    backend >> secrets
    backend >> cloudwatch

    backend >> sns_topic
    usage_scaling_group >> backend
    peaktime_scaling_group >> backend
    cloudwatch_alarms >> backend

    cognito >> alb >> waf >> frontend
    frontend >> s3
    frontend >> secrets
    frontend >> cloudwatch
    usage_scaling_group >> frontend
    peaktime_scaling_group >> frontend
    cloudwatch_alarms >> frontend

    frontend >> Edge() << backend
