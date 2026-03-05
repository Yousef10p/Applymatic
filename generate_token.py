import os
from google_auth_oauthlib.flow import InstalledAppFlow

# This gives your app full permission to read/write to your Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    print("Opening browser to log into Google...")
    # This reads your credentials and opens the login screen
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    # After you log in, this saves your personal master key!
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
        
    print("SUCCESS! Your human 'token.json' file has been created.")

if __name__ == '__main__':
    main()