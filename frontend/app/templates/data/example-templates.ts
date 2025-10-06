import { TemplateData } from '@/types/templates'

const GENERAL_TEMPLATE = `<h2>1. Meeting Overview</h2>
<ul>
  <li>
    <p><strong>Date:</strong></p>
  </li>
  <li>
    <p><strong>Title:</strong></p>
  </li>
  <li>
    <p><strong>Purpose/Objective:</strong></p>
  </li>
</ul>
<h2>2. Attendees</h2>
<p>List all the named attendees including roles/departments if mentioned. If none are named leave this blank.</p>
<ul>
  <li><p>Attendee 1</p></li>
  <li><p>Attendee 2</p></li>
</ul>
<h2>3. Executive Summary</h2>
<p>Three to five sentence summary of the meeting.</p>
<h2>4. Discussion Points</h2>
<ul>
  <li><p>Present in chronological order</p></li>
  <li><p>Group related topics under clear subheadings</p></li>
  <li><p>Include different perspectives and debates</p></li>
  <li><p>Capture the reasoning behind discussions</p></li>
  <li><p>Note any data or evidence presented</p></li>
  <li><p>Highlight concerns raised and how they were addressed</p></li>
  <li>
    <p>Err on the side of including more detail rather than less</p>
  </li>
</ul>
<h2>5. Key Decisions</h2>
<ul>
  <li><p>Clear statement of each decision made</p></li>
  <li><p>Include context and rationale</p></li>
  <li><p>Note who made or approved each decision (if specified)</p></li>
  <li><p>Record any dissenting opinions</p></li>
</ul>
<h2>6. Action Items</h2>
<ul>
  <li><p>List specific tasks assigned</p></li>
</ul>
<ul>
  <li><p>Include responsible parties (if identified)</p></li>
  <li><p>Note deadlines or timeframes</p></li>
  <li><p>Specify any dependencies or resources needed</p></li>
</ul>
<h2>7. Next Steps</h2>
<ul>
  <li><p>Document any planned follow-up meetings</p></li>
  <li><p>Note upcoming milestones or deadlines</p></li>
  <li><p>List any pending items for future discussion</p></li>
</ul>`

export const exampleDocumentTemplates: TemplateData[] = [
  {
    name: 'Meeting Minutes',
    type: 'document',
    description: 'Standard template for recording meeting minutes',
    content:
      '<h2>Meeting Information</h2><p><strong>Date:</strong> [Date]</p><p><strong>Time:</strong> [Time]</p><p><strong>Attendees:</strong> [List of attendees]</p><h2>Agenda Items</h2><ul><li>[Agenda item 1]</li><li>[Agenda item 2]</li></ul><h2>Action Items</h2><ul><li>[Action item 1 - Assigned to: Name - Due: Date]</li><li>[Action item 2 - Assigned to: Name - Due: Date]</li></ul><h2>Next Steps</h2><p>[Next meeting date and any follow-up actions]</p>',
    questions: null,
  },
  {
    name: 'Project Kickoff',
    type: 'document',
    description: 'Template for project kickoff meetings',
    content:
      '<h2>Project Overview</h2><p><strong>Project Name:</strong> [Project Name]</p><p><strong>Project Manager:</strong> [PM Name]</p><p><strong>Start Date:</strong> [Start Date]</p><p><strong>End Date:</strong> [End Date]</p><h2>Objectives</h2><ul><li>[Objective 1]</li><li>[Objective 2]</li></ul><h2>Team Members</h2><ul><li>[Team member 1 - Role]</li><li>[Team member 2 - Role]</li></ul><h2>Key Milestones</h2><ul><li>[Milestone 1 - Date]</li><li>[Milestone 2 - Date]</li></ul><h2>Risks and Mitigation</h2><ul><li>[Risk 1 - Mitigation strategy]</li><li>[Risk 2 - Mitigation strategy]</li></ul>',
    questions: null,
  },
  {
    name: 'Weekly Standup',
    type: 'document',
    description: 'Template for weekly team standup meetings',
    content:
      '<h2>Weekly Standup</h2><p><strong>Week of:</strong> [Date Range]</p><h2>Team Updates</h2><h3>[Team Member 1]</h3><ul><li><strong>Completed:</strong> [What was completed]</li><li><strong>In Progress:</strong> [Current work]</li><li><strong>Blockers:</strong> [Any blockers or challenges]</li></ul><h3>[Team Member 2]</h3><ul><li><strong>Completed:</strong> [What was completed]</li><li><strong>In Progress:</strong> [Current work]</li><li><strong>Blockers:</strong> [Any blockers or challenges]</li></ul><h2>Upcoming Priorities</h2><ul><li>[Priority 1]</li><li>[Priority 2]</li></ul><h2>Action Items</h2><ul><li>[Action item - Owner - Due date]</li></ul>',
    questions: null,
  },
  {
    name: 'My General',
    type: 'document',
    description: 'The General template from Minute which you can customise.',
    content: GENERAL_TEMPLATE,
    questions: null,
  },
]

export const exampleFormTemplates: TemplateData[] = [
  {
    name: 'My Care Assessment',
    type: 'form',
    description: 'A care assessment form',
    content: `You are an experienced social care worker in the UK. You are helping to complete a Care Assessment for a service user. The service user is a person who may be in need of care. You are helping to compile the information required to write a Care Assessment for the service user based on the transcript of the meeting.
Here are the general guidelines to follow:
Write in the third person pronouns for the service user.
Focus on documenting the actual conversation and agreed support.
Important: do not make any analysis, assumptions or judgements about the service user's capabilities.
Include quotes from the candidate if it supports the question
Provide as much detail as possible.
`,
    questions: [
      {
        title: 'What Matters to Me',
        description: 'What is the most important to service user?',
        position: 0,
      },
      {
        title: 'Changes Since Last Review',
        description:
          'Has anything changed since your last "My Assessment", "My Support Plan", or "My Review"? Any changes to long-term health conditions or new diagnoses?',
        position: 1,
      },
      {
        title: 'Daily Life and Routine',
        description:
          'What is your daily routine? (e.g. Tell me how you get washed/dressed and manage your meals and medication.). Who do you see? (e.g. Do you volunteer, attend college or clubs, and how do you get there?). What do you do yourself? (e.g. Shopping, paying bills, laundry, cleaning.). Are you helping to look after anyone? (e.g. Parenting responsibilities.)',
        position: 2,
      },
      {
        title: 'Health, Environment, and Safety',
        description:
          'What is the status of any health conditions and your living environment? (e.g. physical and psychological wellbeing, home setup). How safe do you feel? Is there anything worrying you? (e.g. Financial concerns.)',
        position: 3,
      },
      {
        title: 'Third-Party Perspectives and Fluctuating Needs',
        description:
          'Is there any information from a third party that supports or differs from your view? Do your needs fluctuate? How does this impact you overall?',
        position: 4,
      },
      {
        title: "Assessor's View on Service Provision",
        description:
          'How is the support currently in place working? Provide factual information only. Comment on the quality of service. Are service providers meeting requirements? (e.g. Are they on time, completing all tasks, any missed calls?). Is there an example of good practice? (e.g. A carer or PA going above and beyond their duties.)',
        position: 5,
      },
      {
        title: 'Eligibility Criteria',
        description:
          'Describe the content of the meeting against Care Act outcomes, which are outlined below. Do not make any assessment about whether the service user meets the eligibility criteria or not.',
        position: 6,
      },
      {
        title: 'Managing and Maintaining Nutrition',
        description:
          'Does the adult have access to food and drink to maintain nutrition and are they able to prepare and consume the food and drink? Examples of circumstances affecting the ability to achieve the outcome: if the adult is eating a restricted or unhealthy diet (e.g. only eats toast), or they may have difficulty in getting to the shops to buy food. Similarly, they may be able to prepare food but have swallowing problems.',
        position: 7,
      },
      {
        title: 'Maintaining Personal Hygiene',
        description:
          'Is the adult able to wash themselves and launder their clothes? Examples of circumstances affecting the ability to achieve the outcome: If the adult cannot reach to wash themselves all over, this is not hygienic. If the adult does not have access to a washing machine and their mobility is poor, clothes and linen may not be properly clean. If the adult cannot buy cleaning products, or cognitively understand how to operate a washing machine, their clothes and linen may not be properly clean.',
        position: 8,
      },
      {
        title: 'Managing Toilet Needs',
        description:
          'Is the adult able to access and use the toilet and manage their own toilet needs? Examples of circumstances affecting the ability to achieve the outcome: If the toilet is no longer accessible due to mobility problems or if the adult takes too long to get to the toilet, they may not be managing their toilet needs. If the adult is unable to maintain their night-time continence, they may not be managing their toilet needs in a way that promotes their dignity.',
        position: 9,
      },
      {
        title: 'Being appropriately clothed',
        description:
          'Is the adult able to dress themselves and be appropriately dressed, for example, in relation to the weather or the activities they are undertaking, which could include work/volunteering? Examples of circumstances affecting the ability to achieve the outcome: If the adult cannot put on or fasten their clothes, they are unlikely to be appropriately dressed. If the adult cannot acquire new clothes when needed, they may not be appropriately dressed e.g. for the change in seasons. The adult may be able to dress themselves in casual clothes unaided but may not be able to dress themselves in more formal work clothes e.g. put on a tie, zip up a dress or clean their shoes, and so would not be appropriately dressed for their circumstances. If they are severely visually impaired, for example, they may be able to dress themselves but not know if clothes are appropriate or clean. Note: This may also affect another outcome in relation to accessing work or volunteering.',
        position: 10,
      },
      {
        title: "Being able to make use of the adult's home safely",
        description:
          'Is the adult able to move around the home safely, including climbing steps, using kitchen facilities and accessing the bathroom/toilet? This also includes their immediate environment e.g. steps to the home. Examples of circumstances affecting the ability to achieve the outcome: If the adult cannot reach certain rooms, they may not be using the home safely or may be unreasonably confined e.g. having to spend all day in bed. If the adult cannot get in or out of the front door (e.g. because they cannot manage the steps), they are unlikely to be using the home safely or have proper access to it. If the adult is unable to use home appliances properly and safely (e.g. cooker, heater), they may not be meeting this outcome.',
        position: 11,
      },
      {
        title: 'Maintaining a habitable home environment',
        description:
          "{Is the adult's home sufficiently clean and maintained to be safe, including having essential amenities? Does the adult require support to sustain the home or maintain amenities such as water, electricity and gas or pay their rent or mortgage? Examples of circumstances affecting the ability to achieve the outcome: If the adult is unable to pay their rent or utility bills (e.g. due to mental or physical incapacity), they will not be able to sustain their home. It may not be a habitable home environment if: the home is damp or in very poor repair, the adult is unable to clean their kitchen, leading to infestation, the adult is hoarding excessively (note: hoarding per se does not determine eligibility; however, the impact of excessive hoarding on the individual's ability to achieve their outcomes, and thereby on their wellbeing, will affect eligibility).}",
        position: 12,
      },
      {
        title:
          'Developing and maintaining family or other personal relationships',
        description:
          "{Is the adult lonely or isolated? Do their needs prevent them from maintaining or developing relationships with family and friends? Examples of circumstances affecting the ability to achieve the outcome: The adult's physical or psychological state may prevent them from making or maintaining relationships e.g. mental ill-health, autism. If the adult is unable to communicate easily and regularly – e.g. they may not have, or be able to use, a phone or computer, they may be unable to leave their home safely, they may be unable to communicate successfully or interact with others – this may prevent them from maintaining or developing relationships with family, friends and others.}",
        position: 13,
      },
      {
        title:
          'Accessing and engaging in work, training, education or volunteering',
        description:
          'Does the adult have the opportunity and/or wish to apply themselves and contribute to society through work, training, education or volunteering? This includes physical access to any facility and support with participation in the relevant activity. Examples of circumstances affecting the ability to achieve the outcome: If the adult is unable to leave their home safely, or communicate successfully, or interact with others, they may not be able to access work, training, education or volunteering. If the adult is unable to access information about opportunities available to them, they are unlikely to be able to engage in activities.',
        position: 14,
      },
      {
        title:
          'Making use of necessary facilities or services in the local community, including public transport, and recreational facilities or services',
        description:
          'Is the adult able to get around in the community safely and able to use facilities such as public transport, shops and recreational facilities? This includes the need for support when attending health care appointments. Examples of circumstances affecting the ability to achieve the outcome: If the adult is unable to walk, or to use public transport unattended or to organise alternative transport (e.g. someone giving them a lift), or does not have money for a taxi, they may not be able to access services locally. As well as formal appointments e.g. health care appointments, this could include informal appointments e.g. being able to go to the library or to meet a friend in a cafe or pub.',
        position: 15,
      },
      {
        title:
          'Carrying out any caring responsibilities the adult has for a child',
        description:
          'Does the adult have any parenting or other caring responsibilities e.g. as a parent, step-parent or grandparent? Examples of circumstances affecting the ability to achieve the outcome: If the individual is not able to take care of others, or feels overwhelmed because of their condition, they may not be able to carry out their caring responsibilities for a child.',
        position: 16,
      },
      {
        title: 'My Agreed Plan',
        description:
          'Who will make what things happen, and by when? Record any referrals made, by whom, and for what.',
        position: 17,
      },
      {
        title: 'My Next Planned Review',
        description:
          'When will it be e.g. approximately 12 months. Where and how? Rationale for decision. Would I like anybody to be with me?',
        position: 18,
      },
    ],
  },
]
