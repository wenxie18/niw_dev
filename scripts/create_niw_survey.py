import json
import os
import socket
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/forms.body']

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_credentials():
    """Gets valid user credentials from storage.
    
    Returns:
        Credentials, the obtained credential.
    """
    creds = None
    token_path = os.path.join(config.CREDENTIALS_PATH, 'token.json')
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                # Try port 8888 first
                port = 8888
                if is_port_in_use(port):
                    print(f"Port {port} is in use, trying alternative port...")
                    port = 0  # Let the system choose an available port
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_FORM_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=port)
                
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Error during authentication: {str(e)}")
                print("Please make sure you have the correct credentials file and try again.")
                raise
    
    return creds

def create_form(service, title, description):
    """Creates a new Google Form.
    
    Args:
        service: Google Forms API service instance
        title: Title of the form
        description: Description of the form
    
    Returns:
        The created form's ID
    """
    # First, create the form with just the title
    form = {
        'info': {
            'title': title
        }
    }
    
    created_form = service.forms().create(body=form).execute()
    form_id = created_form['formId']
    
    # Then, update the form with description using batchUpdate
    update_request = {
        'requests': [{
            'updateFormInfo': {
                'info': {
                    'title': title,
                    'description': description
                },
                'updateMask': 'title,description'
            }
        }]
    }
    
    service.forms().batchUpdate(formId=form_id, body=update_request).execute()
    return form_id

def add_section(service, form_id, title, description, index):
    """Adds a section to the form.
    
    Args:
        service: Google Forms API service instance
        form_id: ID of the form
        title: Section title
        description: Section description
        index: Position of the section in the form
    """
    request = {
        'requests': [{
            'createItem': {
                'item': {
                    'title': title,
                    'description': description,
                    'pageBreakItem': {}
                },
                'location': {
                    'index': index
                }
            }
        }]
    }
    
    try:
        service.forms().batchUpdate(formId=form_id, body=request).execute()
        print(f"Successfully added section: {title}")
        return True
    except HttpError as error:
        print(f"Error adding section '{title}': {error}")
        return False

def add_question(service, form_id, question, question_type='TEXT', max_retries=3, delay=1, question_index=0):
    """Adds a question to the form with retry logic.
    
    Args:
        service: Google Forms API service instance
        form_id: ID of the form
        question: Question text
        question_type: Type of question (TEXT, PARAGRAPH_TEXT, etc.)
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        question_index: Position of the question in the section
    """
    request = {
        'requests': [{
            'createItem': {
                'item': {
                    'title': question,
                    'questionItem': {
                        'question': {
                            'required': True,
                            'textQuestion': {}
                        }
                    }
                },
                'location': {
                    'index': question_index
                }
            }
        }]
    }
    
    for attempt in range(max_retries):
        try:
            service.forms().batchUpdate(formId=form_id, body=request).execute()
            print(f"Successfully added question: {question}")
            time.sleep(delay)  # Add delay between requests
            return True
        except HttpError as error:
            if 'RATE_LIMIT_EXCEEDED' in str(error):
                if attempt < max_retries - 1:
                    print(f"Rate limit exceeded, waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print(f"Failed to add question after {max_retries} attempts: {question}")
                    return False
            else:
                print(f"Error adding question '{question}': {error}")
                return False

def main():
    # Load the survey questions
    survey_path = os.path.join(config.DATA_PATH, 'survey_questions_mapping_v1.json')
    with open(survey_path, 'r') as f:
        survey_data = json.load(f)
    
    # Get credentials and build service
    creds = get_credentials()
    service = build('forms', 'v1', credentials=creds)
    
    # Create the form
    form_title = "NIW Petition Information Survey"
    form_description = """
    This survey collects information needed for your National Interest Waiver (NIW) petition.
    Please provide accurate and detailed information for each question.
    All information will be used to prepare your NIW petition documents.
    """
    
    form_id = create_form(service, form_title, form_description)
    print(f"Created form with ID: {form_id}")
    
    # Add sections and questions
    total_items = 0  # Track total number of items added
    failed_questions = []
    
    # Use sections in their original order since Google Forms adds new items at the top
    sections = list(survey_data['sections'].items())
    
    for section_key, section in sections:
        # First add the section header
        if not add_section(service, form_id, section['title'], section['description'], total_items):
            print(f"Failed to add section: {section['title']}")
            continue
        
        total_items += 1  # Increment for section header
        
        # Create a batch request for all questions in this section
        requests = []
        for question_index, (key, question) in enumerate(section['questions'].items()):
            requests.append({
                'createItem': {
                    'item': {
                        'title': question,
                        'questionItem': {
                            'question': {
                                'required': True,
                                'textQuestion': {}
                            }
                        }
                    },
                    'location': {
                        'index': total_items + question_index
                    }
                }
            })
        
        # Add all questions at once
        if requests:
            try:
                service.forms().batchUpdate(
                    formId=form_id,
                    body={'requests': requests}
                ).execute()
                print(f"Successfully added questions for section: {section['title']}")
                total_items += len(requests)  # Increment for all questions added
            except HttpError as error:
                print(f"Error adding questions for section '{section['title']}': {error}")
                failed_questions.extend([(key, question) for key, question in section['questions'].items()])
        
        time.sleep(1)  # Add delay between sections
    
    # Retry failed questions
    if failed_questions:
        print("\nRetrying failed questions...")
        time.sleep(60)  # Wait a minute before retrying
        for key, question in failed_questions:
            if not add_question(service, form_id, question, delay=2):
                print(f"Failed to add question after retry: {question}")
    
    print(f"\nForm creation completed. You can access your form at:")
    print(f"https://docs.google.com/forms/d/{form_id}/edit")

if __name__ == '__main__':
    main() 