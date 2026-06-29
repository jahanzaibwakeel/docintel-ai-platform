# DocIntel Mobile

Expo mobile companion app for the AI Document Intelligence Platform.

## Run

```powershell
npm install
npm run start
```

Set the API URL before starting:

```powershell
$env:EXPO_PUBLIC_API_URL="http://localhost:8000/api/v1"
npm run start
```

Use your computer LAN IP instead of `localhost` when testing on a physical phone.

## Current Features

- Sign in and create account.
- Persist JWT securely enough for local development using AsyncStorage.
- Select workspace.
- Upload PDF documents using the native document picker.
- List documents and statuses.
- View summaries, document type, risk flags, and intelligence.
- Run semantic search.
- Ask questions across the selected workspace.
- Ask questions and view saved chat history.
- Delete documents.

## Next Mobile Increment

- Authenticated PDF preview.
- Push notifications for processing completion and deadline reminders.
- Offline cache for recent document summaries.
