import { DialogueEntry } from '@/lib/client'
import { saveAs } from 'file-saver'
import { asBlob } from 'html-docx-js-typescript'

function getDocumentStyles(): string {
  return `
    <style>
      body {
        white-space: pre-wrap;
        font-family: Helvetica, Arial, sans-serif;
        font-size: 11pt;
      }
      p {
        margin: 0;
        padding: 0;
        line-height: 1.15;
      }
      pre, code {
        font-family: 'Courier New', Courier, monospace;
      }
      blockquote {
        margin-left: 20px;
        padding-left: 10px;
        border-left: 3px solid #ccc;
      }
    </style>
  `
}

function formatTranscript(transcript: DialogueEntry[]): string {
  return transcript
    .map(
      (entry) =>
        `<p><strong>${entry.speaker}</strong>: ${entry.text}</p><p>&nbsp;</p>`
    )
    .join('\n')
}

function preprocessHtml(html: string, transcript: DialogueEntry[]): string {
  // Handle line breaks and empty paragraphs
  const processedHtml = html
    .replace(/<br\s*\/?>/gi, '</p><p>')
    .replace(/<p>\s*<\/p>/gi, '<p>&nbsp;</p>')

  const formattedTranscript = formatTranscript(transcript)

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?mso-application progid="Word.Document"?>
<html xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns:m="http://schemas.microsoft.com/office/2004/12/omml"
      xmlns:v="urn:schemas-microsoft-com:vml"
      xmlns:o="urn:schemas-microsoft-com:office:office">
    <head>
      ${getDocumentStyles()}
      <xml>
        <w:WordDocument>
          <w:View>Print</w:View>
          <w:Zoom>100</w:Zoom>
          <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
      </xml>
      <style>
        @page Section1 {
          size: 8.5in 11.0in;
          margin: 1.0in 1.0in 1.0in 1.0in;
          mso-header-margin: .5in;
          mso-footer-margin: .5in;
          mso-footer: f1;
        }
        div.Section1 { page: Section1; }
        div.f1 {
          mso-element: footer;
          margin: 0in 0in 0in 0in;
          font-size: 11pt;
        }
        /* Hide footer in browser but not in Word */
        @media screen {
          div.f1 {
            display: none;
          }
        }
      </style>
    </head>
    <body>
      <div class="Section1">
        ${processedHtml}
        <p>&nbsp;</p>
        <p><strong>Meeting Transcript:</strong></p>
        <p>&nbsp;</p>
        ${formattedTranscript}
      </div>
      <div class="f1">
        <p style="text-align:center">
          <span style="font-family: Arial;">OFFICIAL SENSITIVE</span>
        </p>
      </div>
    </body>
</html>`
}

async function convertHTMLToWordAndDownload(
  htmlContent: string,
  transcript: DialogueEntry[],
  fileName: string = 'ai-minutes.docx'
): Promise<void> {
  const processedHtml = preprocessHtml(htmlContent, transcript)
  const result = await asBlob(processedHtml)
  const blob = result instanceof Blob ? result : new Blob([result])

  saveAs(blob, fileName)
}

export function removeCitations(text: string): string {
  const citationRegex = /\s*\[\d+\](\s*\.)?/g
  return text.replace(citationRegex, (match, punctuation) => {
    return punctuation ? '.' : ''
  })
}

async function convertAIMinutesToWordDoc(
  html: string,
  transcript: DialogueEntry[],
  fileName: string = 'document.docx'
): Promise<void> {
  const cleanedHTML = removeCitations(html)
  await convertHTMLToWordAndDownload(cleanedHTML, transcript, fileName)
}

export default convertAIMinutesToWordDoc
