from citation_map import generate_citation_map
import config

if __name__ == '__main__':
    # This is my Google Scholar ID. Replace this with your ID.
    scholar_id = 'KreqRjAAAAAJ&hl'
    email = 'vaneshieh@gmail.com'

    generate_citation_map(scholar_id, output_path=f'{config.OUTPUT_BASE_FOLDER}/vaneshieh@gmail.com/citation_map.html',
                          csv_output_path=f'{config.OUTPUT_BASE_FOLDER}/vaneshieh@gmail.com/citation_info.csv')