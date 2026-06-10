import React from 'react'
import { Separator } from '@/components/ui/separator'

export default function PrivacyPage() {
  return (
    <div className="govuk-width-container govuk-main-wrapper">
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Privacy Notice</h1>

          <p className="govuk-body-l">
            This notice sets out how we will use your personal data, and your
            rights. It is made under Articles 13 and/or 14 of the UK General Data
            Protection Regulation (UK GDPR).
          </p>

          <section>
            <h2 className="govuk-heading-l">Your data</h2>

            <h3 className="govuk-heading-m">Purpose</h3>
            <p className="govuk-body">
              Overall the purpose is to provide AI support for the minute-takers.
              To do this we will process personal data as access credentials to
              the AI Tool, to ensure secure access and auditability.
            </p>
            <p className="govuk-body">
              The AI minuting tool creates the following three outputs:
            </p>
            <ul className="govuk-list govuk-list--bullet govuk-list--spaced">
              <li>an audio recording of a meeting, which is used to create:</li>
              <li>a granular transcript of a meeting</li>
              <li>a high-level draft minute in the style of a Cabinet minute.</li>
            </ul>
            <p className="govuk-body">
              These outputs will contain the personal data of attendees and
              individuals that form part of the meeting.
            </p>
            <h3 className="govuk-heading-m">The data</h3>
            <p className="govuk-body">
              We will process the following personal data:
            </p>
            <p className="govuk-heading-s">Users of the AI Tool</p>
            <ul className="govuk-list govuk-list--bullet govuk-list--spaced">
              <li>Name</li>
              <li>Organisational Email</li>
            </ul>
            <p className="govuk-heading-s">Minutes Process</p>
            <ul className="govuk-list govuk-list--bullet govuk-list--spaced">
              <li>Audio Recording of the meeting</li>
              <li>Transcript of meetings</li>
              <li>Draft minutes of the meetings</li>
            </ul>

            <h3 className="govuk-heading-m">
              Legal basis of processing
            </h3>
            <p className="govuk-body">
              The legal basis for processing your personal data is:
            </p>
            <p className="govuk-body">
              It is necessary for the purposes of the legitimate interests pursued
              by the controller or by a third party. In this case those are,
              providing secure access to Cabinet Office platforms and
              applications.
            </p>
            <p className="govuk-body">
              Regarding the recording of the meeting the legal basis will be the
              data subject consents.
            </p>

            <h3 className="govuk-heading-m">
              Sensitive personal data
            </h3>
            <p className="govuk-body">
              Sensitive personal data is personal data revealing racial or ethnic
              origin, political opinions, religious or philosophical beliefs, or
              trade union membership, and the processing of genetic data,
              biometric data for the purpose of uniquely identifying a natural
              person, data concerning health or data concerning a natural
              person&apos;s sex life or sexual orientation.
            </p>
            <p className="govuk-body">
              The legal basis for processing your sensitive personal data is:
            </p>
            <p className="govuk-body">
              Processing is necessary for reasons of substantial public interest
              for the exercise of a function of the Crown, a Minister of the
              Crown, or a government department; the exercise of a function
              conferred on a person by an enactment; or the exercise of a function
              of either House of Parliament. In this case providing accurate
              minutes of Ministerial meetings.
            </p>

            <h3 className="govuk-heading-m">Recipients</h3>
            <p className="govuk-body">
              Your personal data will be shared by us with:
            </p>
            <ul className="govuk-list govuk-list--bullet govuk-list--spaced">
              <li>
                Data processors that provide our corporate IT infrastructure,
                including email, document management and storage services. Applies
                to access credentials only.
              </li>
              <li>
                AWS and Microsoft, on an encrypted basis, as the providers of the
                app hosting and the Large Language Model being used by the AI
                Minute Tool.
              </li>
            </ul>

            {/* <h3 className="pt-4 text-xl font-semibold">Retention</h3>
          <p className="leading-7 text-muted-foreground">
            Your personal data will be kept by us for:
          </p>
          <ul className="list-inside list-disc pl-4 text-muted-foreground">
            <li>
              Access Credentials for users – retained whilst the individual
              requires access to the tool. Usage will be reviewed after six
              months from the start of the project.
            </li>
            <li>
              Audio Recordings – automatically deleted as soon as the window is
              closed and not sent to local or permanent storage. Accessible
              within the tool for a maximum of 10 hours.
            </li>
            <li>
              The Transcript - automatically deleted as soon as the window is
              closed and not sent to local or permanent storage.
            </li>
            <li>
              AI minutes - These do not replace the official minute, and are
              only used to inform it. These will be deleted once the final
              official minutes have been approved.
            </li>
          </ul> */}
          </section>

          <section>
            <h2 className="govuk-heading-l">Your rights</h2>
            <ul className="govuk-list govuk-list--bullet govuk-list--spaced">
              <li>
                You have the right to request information about how your personal
                data are processed, and to request a copy of that personal data.
              </li>
              <li>
                You have the right to request that any inaccuracies in your
                personal data are rectified without delay.
              </li>
              <li>
                You have the right to request that any incomplete personal data
                are completed, including by means of a supplementary statement.
              </li>
              <li>
                You have the right to request that your personal data are erased
                if there is no longer a justification for them to be processed.
              </li>
              <li>
                You have the right in certain circumstances (for example, where
                accuracy is contested) to request that the processing of your
                personal data is restricted.
              </li>
              <li>
                You have the right to object to the processing of your personal
                data where it is processed for direct marketing purposes.
              </li>
              <li>
                You have the right to object to the processing of your personal
                data.
              </li>
              <li>
                You have the right to withdraw consent to the processing of your
                personal data at any time.
              </li>
              <li>
                You have the right to request a copy of any personal data you have
                provided, and for this to be provided in a structured, commonly
                used and machine-readable format.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="govuk-heading-l">International transfers</h2>
            <p className="govuk-body">
              As your personal data is stored on our Corporate IT infrastructure,
              and shared with our data processors, it may be transferred and
              stored securely outside the UK. Where that is the case it will be
              subject to equivalent legal protection through an adequacy decision,
              reliance on Standard Contractual Clauses, or reliance on a UK
              International Data Transfer Agreement.
            </p>
            <p className="govuk-body">
              As your data will be shared with AWS and Microsoft who provides
              hosting and the provision of the Azure LLM services to us, it may be
              stored securely outside the UK. Where that is the case it will be
              subject to equivalent legal protection through an adequacy decision
              by the UK Government.
            </p>
          </section>

          <section>
            <h2 className="govuk-heading-l">Complaints</h2>
            <p className="govuk-body">
              If you consider that your personal data has been misused or
              mishandled, you may make a complaint to the Information
              Commissioner, who is an independent regulator. The Information
              Commissioner can be contacted at: Information Commissioner&apos;s
              Office, Wycliffe House, Water Lane, Wilmslow, Cheshire, SK9 5AF, or
              0303 123 1113, or icocasework@ico.org.uk. Any complaint to the
              Information Commissioner is without prejudice to your right to seek
              redress through the courts.
            </p>
          </section>

          <section>
            <h2 className="govuk-heading-l">Contact details</h2>
            <p className="govuk-body">
              The data controller for your personal data is the Cabinet Office.
              The contact details for the data controller are: Cabinet Office, 70
              Whitehall, London, SW1A 2AS, or 0207 276 1234, or you can use this
              webform.
            </p>
            <p className="govuk-body">
              The contact details for the data controller&apos;s Data Protection
              Officer are: dpo@cabinetoffice.gov.uk.
            </p>
            <p className="govuk-body">
              The Data Protection Officer provides independent advice and
              monitoring of Cabinet Office&apos;s use of personal information.
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
