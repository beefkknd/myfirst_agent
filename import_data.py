
import csv
import json

import requests

CHUNK_SIZE = 5000

def import_to_es(csv_file, es_url):
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        bulk_data = []
        for i, row in enumerate(reader):
            action = {"index": {"_index": "vessel_index"}}
            # Convert numeric fields to numbers
            for field in ["LAT", "LON", "SOG", "COG", "Heading", "Length", "Width", "Draft"]:
                if row[field]:
                    try:
                        row[field] = float(row[field])
                    except ValueError:
                        row[field] = None # or some other default value
                else:
                    row[field] = None

            bulk_data.append(json.dumps(action))
            bulk_data.append(json.dumps(row))

            if (i + 1) % CHUNK_SIZE == 0:
                send_bulk_request(es_url, bulk_data)
                bulk_data = []

        if bulk_data:
            send_bulk_request(es_url, bulk_data)

def send_bulk_request(es_url, bulk_data):
    headers = {'Content-Type': 'application/x-ndjson'}
    response = requests.post(es_url, data='\n'.join(bulk_data) + '\n', headers=headers)
    if response.status_code != 200:
        print(f"Error sending bulk request: {response.text}")
    else:
        print(f"Successfully indexed {len(bulk_data)//2} documents.")

if __name__ == "__main__":
    es_url = "http://localhost:9200/_bulk"
    csv_file = "data/AIS_2022_01_01.csv"
    import_to_es(csv_file, es_url)
