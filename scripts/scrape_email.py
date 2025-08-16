from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin  # For combining base and relative URLs
import requests
import io
import PyPDF2  # For extracting text from PDFs

# Function to extract email addresses from a webpage
def extract_emails(text):
    # Regex pattern to match standard email addresses
    standard_email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    standard_emails = re.findall(standard_email_pattern, text)

    # # Regex pattern to match text after "Email:", "e-mail:", or "contact:"
    # email_keyword_pattern = r"(?:email|e-mail|contact)[:\s]*(.*?)(?:\n|$)"
    # email_keyword_matches = re.findall(email_keyword_pattern, text, re.IGNORECASE)

    # # Regex pattern to match mailto links
    # mailto_pattern = r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    # mailto_emails = re.findall(mailto_pattern, text)

    # Combine all email matches
    all_emails = standard_emails #+ email_keyword_matches + mailto_emails
    return all_emails

# Function to extract text from a PDF URL
def extract_text_from_pdf(pdf_url):
    try:
        # Download the PDF content
        response = requests.get(pdf_url)
        response.raise_for_status()

        # Stream the PDF content
        with io.BytesIO(response.content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_url}: {e}")
        return ""

# Function to analyze a webpage for email addresses
def analyze_page(driver):
    try:
        # Get the page source and parse it with BeautifulSoup
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract all text from the page
        page_text = soup.get_text()

        # Find email addresses in the text
        emails = extract_emails(page_text)

        # Find mailto links in the HTML
        mailto_links = soup.find_all('a', href=lambda href: href and href.startswith('mailto:'))
        for link in mailto_links:
            email = link['href'].replace('mailto:', '')
            emails.append(email)

        return emails
    except Exception as e:
        print(f"Error analyzing page: {e}")
        return []

# Function to process CV (PDF) and extract emails
def process_cv(driver, tab_name, full_url):
    try:
        print(f"Checking CV file on tab: {tab_name}")
        
        # Locate the iframe containing the PDF
        iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'drive.google.com')]")
        pdf_url = iframe.get_attribute('src')

        # Extract the download URL from the parent element
        pdf_download_url = driver.find_element(By.XPATH, "//div[@data-embed-download-url]").get_attribute('data-embed-download-url')
        print(f"Found PDF download URL: {pdf_download_url}")

        # Extract text from the PDF
        pdf_text = extract_text_from_pdf(pdf_download_url)
        print('Extracting email from CV PDF.....')
        pdf_emails = extract_emails(pdf_text)
        return pdf_emails
    except Exception as e:
        print(f"Error extracting text from CV: {e}")
        return []

# # Function to crawl a homepage and its tabs for emails
# def crawl_homepage(driver, homepage_url, visited=None):
#     if visited is None:
#         visited = set()  # Track visited pages to avoid recursion

#     try:
#         emails = set()  # Use a set to avoid duplicate emails

#         # Skip if the page has already been visited
#         if homepage_url in visited:
#             return list(emails)
#         visited.add(homepage_url)  # Mark this page as visited

#         # Navigate to the homepage
#         driver.get(homepage_url)
#         time.sleep(3)  # Wait for the page to load

#         # Analyze the homepage itself
#         print(f"Crawling homepage: {homepage_url}")
#         homepage_emails = analyze_page(driver)
#         emails.update(homepage_emails)

#         # Find all tab elements using a flexible XPath
#         tab_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'aJHbb') or contains(@class, 'tab') or contains(@class, 'nav-link')]")
#         print(f"Found {len(tab_elements)} tabs to crawl.")

#         # Iterate through the tabs
#         for i in range(len(tab_elements)):
#             try:
#                 # Re-locate the tab elements after each navigation
#                 tab_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'aJHbb') or contains(@class, 'tab') or contains(@class, 'nav-link')]")
#                 if i >= len(tab_elements):
#                     break  # Exit if there are no more tabs

#                 tab = tab_elements[i]
#                 tab_name = tab.text.strip()  # Get the name of the tab
#                 print(f"Crawling tab: {tab_name}")

#                 # Get the relative URL from the href attribute
#                 relative_url = tab.get_attribute('href')
#                 if not relative_url:
#                     print(f"Skipping tab {tab_name}: No href attribute found.")
#                     continue

#                 # Construct the full URL
#                 full_url = urljoin(homepage_url, relative_url)
#                 if full_url in visited and "cv" not in tab_name.lower():
#                     print(f"Skipping tab {tab_name}: Already visited.")
#                     continue

#                 print(f"Navigating to: {full_url}")

#                 # Navigate to the full URL
#                 driver.get(full_url)
#                 time.sleep(3)  # Wait for the new content to load

#                 # Analyze the content of the tab
#                 tab_emails = analyze_page(driver)
#                 emails.update(tab_emails)

#                 # Check for embedded PDFs (e.g., CV)
#                 if "cv" in tab_name.lower():
#                     cv_emails = process_cv(driver, tab_name, full_url)
#                     emails.update(cv_emails)

#                 # Mark this URL as visited
#                 visited.add(full_url)
#             except Exception as e:
#                 print(f"Error crawling tab {tab_name}: {e}")

#         return list(emails)
#     except Exception as e:
#         print(f"Error crawling homepage {homepage_url}: {e}")
#         return []

# Function to crawl a homepage and its tabs for emails
def crawl_homepage(driver, homepage_url, visited=None):
    if visited is None:
        visited = set()  # Track visited pages to avoid recursion

    try:
        emails = set()  # Use a set to avoid duplicate emails

        # Skip if the page has already been visited
        if homepage_url in visited:
            return list(emails)
        visited.add(homepage_url)  # Mark this page as visited

        # Navigate to the homepage
        driver.get(homepage_url)
        time.sleep(3)  # Wait for the page to load

        # Analyze the homepage itself
        print(f"Crawling homepage: {homepage_url}")
        homepage_emails = analyze_page(driver)
        emails.update(homepage_emails)

        # Find all tab elements using a flexible XPath
        # Case 1: Tabs inside <div class="menu">
        menu_tabs = driver.find_elements(By.XPATH, "//div[@class='menu']//a")
        # Case 2: Tabs with specific classes (existing logic)
        class_tabs = driver.find_elements(By.XPATH, "//a[contains(@class, 'aJHbb') or contains(@class, 'tab') or contains(@class, 'nav-link')]")
        
        # Combine both sets of tabs
        tab_elements = menu_tabs + class_tabs
        print(f"Found {len(tab_elements)} tabs to crawl.")

        # Iterate through the tabs
        for i in range(len(tab_elements)):
            try:
                # Re-locate the tab elements after each navigation
                menu_tabs = driver.find_elements(By.XPATH, "//div[@class='menu']//a")
                class_tabs = driver.find_elements(By.XPATH, "//a[contains(@class, 'aJHbb') or contains(@class, 'tab') or contains(@class, 'nav-link')]")
                tab_elements = menu_tabs + class_tabs
                if i >= len(tab_elements):
                    break  # Exit if there are no more tabs

                tab = tab_elements[i]
                tab_name = tab.text.strip()  # Get the name of the tab
                print(f"Crawling tab: {tab_name}")

                # Get the relative URL from the href attribute
                relative_url = tab.get_attribute('href')
                if not relative_url:
                    print(f"Skipping tab {tab_name}: No href attribute found.")
                    continue

                # Construct the full URL
                full_url = urljoin(homepage_url, relative_url)
                if full_url in visited and "cv" not in tab_name.lower():
                    print(f"Skipping tab {tab_name}: Already visited.")
                    continue

                print(f"Navigating to: {full_url}")

                # Navigate to the full URL
                driver.get(full_url)
                time.sleep(3)  # Wait for the new content to load

                # Analyze the content of the tab
                tab_emails = analyze_page(driver)
                emails.update(tab_emails)

                # Check for embedded PDFs (e.g., CV)
                if "cv" in tab_name.lower():
                    cv_emails = process_cv(driver, tab_name, full_url)
                    emails.update(cv_emails)

                # Mark this URL as visited
                visited.add(full_url)
            except Exception as e:
                print(f"Error crawling tab {tab_name}: {e}")

        return list(emails)
    except Exception as e:
        print(f"Error crawling homepage {homepage_url}: {e}")
        return []
    
# Function to scrape Google Scholar profile and find homepage
def scrape_email_from_google_scholar_profile(profile_url):
    try:
        # Set up Selenium to visit the Google Scholar profile
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode (no GUI)
        driver = webdriver.Chrome(service=Service(), options=options)
        driver.get(profile_url)

        # Wait for the "Homepage" button to load
        wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
        homepage_button = wait.until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'gsc_prf_ila') and contains(text(), 'Homepage')]"))
        )
        homepage_url = homepage_button.get_attribute('href')

        # Crawl the homepage and its tabs for emails
        emails = crawl_homepage(driver, homepage_url)
        driver.quit()
        return emails
    except Exception as e:
        print(f"Error scraping Google Scholar profile: {e}")
        return []



if __name__ == '__main__':
    # Example usage
    profile_url_dict={'yakov': "https://scholar.google.com/citations?user=OyysmJgAAAAJ&hl=en",
                    'sarah': "https://scholar.google.com/citations?user=zBeOc3AAAAAJ&hl=en",
                    'yanjun': "https://scholar.google.com/citations?user=lTUM3B0AAAAJ&hl=en",
                    'gijs': "https://scholar.google.com/citations?user=aiHz0J4AAAAJ&hl=en",
                    'maarten': "https://scholar.google.com/citations?user=ekCd0LoAAAAJ&hl=en"
    }

    # Loop through each profile URL and scrape emails
    for name, profile_url in profile_url_dict.items():
        emails = scrape_email_from_google_scholar_profile(profile_url)
        print(f"Found emails for {name}: {emails}")