import pandas as pd
from PIL import Image
from pathlib import Path
from google.cloud import storage, datastore
from tqdm import tqdm

DATASET_PATH = Path("/home/andretelfer/berlin2022/datasets/CUv3/")
BUCKET_NAME = "mgs-webapp"
ORIGIN = "Data from Carleton University, Labels from TU Berlin"

datastore_client = datastore.Client()
storage_client = storage.Client()

# Load the dataset
manual_scores = pd.read_excel(DATASET_PATH / 'mgs_scores.xlsx')
manual_scores = manual_scores.dropna(subset=["Mean_Scorer4"]) # Drop rows without a score

df = manual_scores.copy()
df['path'] = df.apply(lambda x: Path("resized-images") / Path(x.Path).parts[-1] / x.Filename, axis=1)
df = df.rename(columns={'Eyes_Scorer4': 'eyes', 'Nose_Scorer4': 'nose', 'Cheeks_Scorer4': 'cheeks', 'Ears_Scorer4': 'ears', 'Whiskers_Scorer4': 'whiskers'})
df = df[['path', 'eyes', 'nose', 'cheeks', 'ears', 'whiskers']]
df = df.fillna(0)
for col in ['eyes', 'nose', 'cheeks', 'ears', 'whiskers']:
    df[col] = df[col].astype(int)
    
# Delete the existing bucket
try:
    bucket = storage_client.get_bucket(BUCKET_NAME)
    bucket.delete(force=True)
except:
    pass

# Create a new bucket
bucket = storage_client.create_bucket(BUCKET_NAME)
print(f"Bucket {bucket.name} created.")

# Update all items in bucket to be public
members = ["allUsers"]
bucket = storage_client.bucket(BUCKET_NAME)
policy = bucket.get_iam_policy(requested_policy_version=3)
policy.bindings.append(
    {"role": "roles/storage.objectViewer", "members": members}
)
bucket.set_iam_policy(policy)

# Delete existing datastore items
query = datastore_client.query(kind="Question")
for entity in query.fetch():
    datastore_client.delete(entity.key)
    
# Add data 
id = 1
for idx, row in tqdm(df.iterrows()):
    item = row.to_dict()
    item['origin'] = ORIGIN
    item['path'] = str(item['path'])
    
    # Upload to google cloud storage
    blob = bucket.blob(f'{id}.png')
    blob.upload_from_filename(str(DATASET_PATH / row.path))
    blob.make_public()
    item['url'] = blob.public_url
    
    # Upload to google datastore
    key = datastore_client.key("Question", id)
    entity = datastore.Entity(key=key)
    entity.update(item)
    datastore_client.put(entity)
    
    # update id
    id += 1