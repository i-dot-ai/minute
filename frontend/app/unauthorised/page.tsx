import React from 'react'

function Unauthorised(): React.JSX.Element {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f9fafb',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        padding: '1rem',
        font: 'inter',
        paddingTop: '4rem',
      }}
    >
      <div
        style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '0.5rem',
          boxShadow:
            '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          maxWidth: '28rem',
          width: '100%',
          textAlign: 'center',
          font: 'inter',
        }}
      >
        <h1
          style={{
            fontSize: '1.5rem',
            fontWeight: 'bold',
            color: '#1f2937',
            marginBottom: '0.75rem',
            font: 'inter',
          }}
        >
          Unauthorised Access
        </h1>

        <p
          style={{
            color: '#4b5563',
            marginBottom: '1.5rem',
          }}
        >
          Sorry, you don&apos;t have permission to access this page. Please
          contact your administrator if you believe this is an error.
        </p>
      </div>
    </div>
  )
}

export default Unauthorised
