import type { TemplateResponse } from '@/lib/client/types.gen'

export const userTemplates = [
  {
    id: '9b8e26e2-88a2-46f3-9563-d972f8370aad',
    updated_datetime: '2026-09-04T10:29:19.467701Z',
    name: 'My Care Assessment gh',
    content:
      "You are an experienced social care worker in the UK. You are helping to complete a Care Assessment for a service user. The service user is a person who may be in need of care. You are helping to compile the information required to write a Care Assessment for the service user based on the transcript of the meeting.\nHere are the general guidelines to follow:\nWrite in the third person pronouns for the service user.\nFocus on documenting the actual conversation and agreed support.\nImportant: do not make any analysis, assumptions or judgements about the service user's capabilities.\nInclude quotes from the candidate if it supports the question\nProvide as much detail as possible.\n",
    description: 'A care assessment form',
    type: 'form',
    questions: null,
    is_default: false,
  },
  {
    id: '5ff2211b-f71d-427b-980d-50dbf3c38bc1',
    updated_datetime: '2026-08-14T08:57:47.315520Z',
    name: 'Project kickoff',
    content:
      '<h2>Project Overview</h2><p><strong>Project Name:</strong> [Project Name]</p><p><strong>Project Manager:</strong> [PM Name]</p><p><strong>Start Date:</strong> [Start Date]</p><p><strong>End Date:</strong> [End Date]</p><h2>Objectives</h2><ul><li><p>[Objective 1]</p></li><li><p>[Objective 2]</p></li></ul><h2>Team Members</h2><ul><li><p>[Team member 1 - Role]</p></li><li><p>[Team member 2 - Role]</p></li></ul><h2>Key Milestones</h2><ul><li><p>[Milestone 1 - Date]</p></li><li><p>[Milestone 2 - Date]</p></li></ul><h2>Risks and Mitigation</h2><ul><li><p>[Risk 1 - Mitigation strategy]</p></li><li><p>[Risk 2 - Mitigation strategy]</p></li></ul><p></p>',
    description:
      'Template for project kickoff meetings Template for project kickoff meetings Template for project kickoff meetings',
    type: 'document',
    questions: null,
    is_default: false,
  },
  {
    id: '1f14032a-0ba8-4ffe-95ab-264cfe6c399f',
    updated_datetime: '2026-08-14T08:55:32.929120Z',
    name: 'My Care',
    content:
      "You are an experienced social care worker in the UK. You are helping to complete a Care Assessment for a service user. The service user is a person who may be in need of care. You are helping to compile the information required to write a Care Assessment for the service user based on the transcript of the meeting.\nHere are the general guidelines to follow:\nWrite in the third person pronouns for the service user.\nFocus on documenting the actual conversation and agreed support.\nImportant: do not make any analysis, assumptions or judgements about the service user's capabilities.\nInclude quotes from the candidate if it supports the question\nProvide as much detail as possible.\n",
    description:
      'A one to one template for a line manager to discuss regularly with their direct reports',
    type: 'form',
    questions: null,
    is_default: false,
  },
  {
    id: '1223f0b9-93b1-46f3-91fd-8fe47f35fe2d',
    updated_datetime: '2026-07-10T15:02:27.462351Z',
    name: 'My Care edited',
    content:
      "You are an experienced social care worker in the UK. You are helping to complete a Care Assessment for a service user. The service user is a person who may be in need of care. You are helping to compile the information required to write a Care Assessment for the service user based on the transcript of the meeting.\nHere are the general guidelines to follow:\nWrite in the third person pronouns for the service user.\nFocus on documenting the actual conversation and agreed support.\nImportant: do not make any analysis, assumptions or judgements about the service user's capabilities.\nInclude quotes from the candidate if it supports the question\nProvide as much detail as possible.\n",
    description: 'A care assessment form',
    type: 'form',
    questions: null,
    is_default: false,
  },
] satisfies Array<TemplateResponse>
