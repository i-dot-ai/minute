import { TemplateData } from '@/app/templates/components/editor/template-editor'

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

export const exampleTemplates: TemplateData[] = [
  {
    name: 'Meeting Minutes',
    description: 'Standard template for recording meeting minutes',
    content:
      '<h2>Meeting Information</h2><p><strong>Date:</strong> [Date]</p><p><strong>Time:</strong> [Time]</p><p><strong>Attendees:</strong> [List of attendees]</p><h2>Agenda Items</h2><ul><li>[Agenda item 1]</li><li>[Agenda item 2]</li></ul><h2>Action Items</h2><ul><li>[Action item 1 - Assigned to: Name - Due: Date]</li><li>[Action item 2 - Assigned to: Name - Due: Date]</li></ul><h2>Next Steps</h2><p>[Next meeting date and any follow-up actions]</p>',
  },
  {
    name: 'Project Kickoff',
    description: 'Template for project kickoff meetings',
    content:
      '<h2>Project Overview</h2><p><strong>Project Name:</strong> [Project Name]</p><p><strong>Project Manager:</strong> [PM Name]</p><p><strong>Start Date:</strong> [Start Date]</p><p><strong>End Date:</strong> [End Date]</p><h2>Objectives</h2><ul><li>[Objective 1]</li><li>[Objective 2]</li></ul><h2>Team Members</h2><ul><li>[Team member 1 - Role]</li><li>[Team member 2 - Role]</li></ul><h2>Key Milestones</h2><ul><li>[Milestone 1 - Date]</li><li>[Milestone 2 - Date]</li></ul><h2>Risks and Mitigation</h2><ul><li>[Risk 1 - Mitigation strategy]</li><li>[Risk 2 - Mitigation strategy]</li></ul>',
  },
  {
    name: 'Weekly Standup',
    description: 'Template for weekly team standup meetings',
    content:
      '<h2>Weekly Standup</h2><p><strong>Week of:</strong> [Date Range]</p><h2>Team Updates</h2><h3>[Team Member 1]</h3><ul><li><strong>Completed:</strong> [What was completed]</li><li><strong>In Progress:</strong> [Current work]</li><li><strong>Blockers:</strong> [Any blockers or challenges]</li></ul><h3>[Team Member 2]</h3><ul><li><strong>Completed:</strong> [What was completed]</li><li><strong>In Progress:</strong> [Current work]</li><li><strong>Blockers:</strong> [Any blockers or challenges]</li></ul><h2>Upcoming Priorities</h2><ul><li>[Priority 1]</li><li>[Priority 2]</li></ul><h2>Action Items</h2><ul><li>[Action item - Owner - Due date]</li></ul>',
  },
  {
    name: 'General',
    description: 'The General template from Minute which you can customise.',
    content: GENERAL_TEMPLATE,
  },
]
