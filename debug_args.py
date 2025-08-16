import argparse
import config

def test_args():
    parser = argparse.ArgumentParser(description="Fill PDF forms based on Google Sheets data.")

    parser.add_argument("--fill", type=str,
                        default=config.DEFAULT_FILL,
                        help="Specify which forms to fill (e.g., 'all', '1145', '9089', '140'). Default is set in config.py.")
                        
    parser.add_argument("--email", type=str,
                        default=config.DEFAULT_EMAIL,
                        help="Specify email address to filter forms (e.g., 'vaneshieh@gmail.com'). If not specified, uses DEFAULT_EMAIL from config.py.")

    args = parser.parse_args()

    print(f"Config DEFAULT_FILL: {config.DEFAULT_FILL}")
    print(f"Config DEFAULT_EMAIL: {config.DEFAULT_EMAIL}")
    print(f"Parsed --fill: {args.fill}")
    print(f"Parsed --email: {args.email}")

if __name__ == "__main__":
    test_args() 