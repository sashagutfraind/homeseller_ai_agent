import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import App from './App';
import './index.css';

// Configure Amplify with deployment outputs
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_23RTFoRtW',
      userPoolClientId: '1t6373o7puuas278psepedc4vn',
      identityPoolId: 'us-east-1:c9a78142-d538-4d0b-8cf8-d01c0da04853',
      loginWith: {
        email: true,
      },
      signUpVerificationMethod: 'code',
      userAttributes: {
        email: {
          required: true,
        },
      },
      allowGuestAccess: false,
      passwordFormat: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireNumbers: true,
        requireSpecialCharacters: true,
      },
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
