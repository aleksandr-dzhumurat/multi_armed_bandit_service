import json
import logging
import os
from typing import Optional, Dict, Tuple, List

import pandas as pd
import numpy as np
import yaml
from pymongo import MongoClient
from bson.objectid import ObjectId
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# from src.prepare_data import load_embedder

MONGO_HOST = os.environ['MONGO_HOST']
logger = logging.getLogger('my_logger')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)

# embedder = load_embedder()


def load_config() -> dict:
    config_path = os.getenv("CONFIG_PATH", "config.yml")
    with open(config_path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


config = load_config()

def artifact_path(artifact_name: str):
    artifacts_dirname  = "service_data"
    return os.path.join(config['root_data_dir'], artifacts_dirname, artifact_name)

def user_tags_ranking(user_actions: Dict, all_tags_df: pd.DataFrame):
    LIKE = 'like'
    DISLIKE = 'dislike'
    tags_df = all_tags_df.copy()
    if len(user_actions) > 0:
        user_negative_tags = pd.json_normalize([i for i in user_actions if i['action']==DISLIKE])
        if user_negative_tags.shape[0] > 0:
            user_negative_tags = user_negative_tags['content_tag'].value_counts().to_frame(name='cnt').reset_index()
            user_negative_tags.columns = ['content_tag', 'cnt']
        user_positive_tags = pd.json_normalize([i for i in user_actions if i['action']==LIKE])
        if user_positive_tags.shape[0] > 0:
            user_positive_tags = user_positive_tags['content_tag'].value_counts().to_frame(name='cnt').reset_index()
            user_positive_tags.columns = ['content_tag', 'cnt']
        if user_negative_tags.shape[0] > 0:  # drop disliked tags
            tags_df = (
                tags_df
                .merge(user_negative_tags, how='left', left_on='tag', right_on='content_tag',suffixes=('','_neg'))
                .query('cnt_neg.isnull()')
                [['tag', 'cnt']]
            )
        if user_positive_tags.shape[0] > 0:
            tags_df = (
                tags_df
                .merge(user_positive_tags, how='left', left_on='tag', right_on='content_tag',suffixes=('','_pos'))
                .sort_values('cnt_pos', ascending=False)
                [['tag', 'cnt', 'cnt_pos']]
            ).head(3)  # add
    return tags_df


class ContentDB:
    def __init__(self):
        self.df = None  # type: Optional[pd.DataFrame]
        self.tags_df = None  # type: Optional[pd.DataFrame]
        # Simple BoW recommendations
        self.embedder = None
        self.corpus_numpy = None
        
    def init_db(self):
        self.df = pd.read_csv(artifact_path('content_db.csv.gz'), compression='gzip')
        self.df['art_tags'] = self.df['art_tags'].fillna(value='')
        self.df['wikipedia'] = self.df['wikipedia'].fillna(value='')
        print('Num artists %d' % self.df.shape[0])
        self.tags_df = pd.read_csv(artifact_path('tags_db.csv.gz'), compression='gzip').query('cnt > 1')
        self.tags_df = self.tags_df[self.tags_df['tag'].str.len() <= 15].copy()
        excluded_tags = ['art']
        self.tags_df.drop(self.tags_df[self.tags_df['tag'].isin(excluded_tags)].index, inplace=True)
        print('Num tags %d' % self.tags_df.shape[0])
        print('Preparing vector DB...')
        self.embedder = TfidfVectorizer(
            analyzer='word',
            lowercase=True,
            token_pattern=r'\b[\w\d]{3,}\b'
        )
        self.embedder.fit(self.df['art_tags'].values)
        self.corpus_numpy = self.embedder.transform(self.df['art_tags'].values)
        print("DB prepared succesfully!")
    
    def get_content(self, content_id: int) -> Dict:
        content_info = self.df.iloc[content_id].to_dict()
        res = {}
        res.update({'artist_movement': content_info['artist_movement']})
        res.update({'field': content_info['artist_field']})
        random_artwork = np.random.choice(json.loads(content_info['artworks']))
        artwork_name = json.dumps(random_artwork.split('/')[-1].split('.')[0].replace('-', ' '))
        res.update({'artworks': random_artwork, 'artwork_name': artwork_name})
        res.update({'artist_id': content_id, 'artist_name': content_info['artist_name'], 'artist_url': content_info['artist_url']})
        for key in res.keys():
            if not isinstance(res[key], str):
                if np.isnan(res[key]):
                    res[key] = 'Empty'
        return res
    
    def recommend(self, user_actions: List[Dict[str, str]], num_recs: int = 10) -> dict:
        user_positive_tags = [i['content_tag'] for i in user_actions if i['action']=='like']
        user_pref = ''
        if len(user_positive_tags) > 0:
            user_pref = ' '.join(user_positive_tags)
            query_embed = self.embedder.transform([user_pref])
            similarities = cosine_similarity(query_embed, self.corpus_numpy).flatten()
            rec_ids = np.argsort(similarities)[::-1][:num_recs]
            recs = self.df.iloc[rec_ids]
        else:
            logger.info('random recommendation')
            recs = self.df.sample(num_recs)
        recs_list = []
        for _, row in recs.sample(3).iterrows():
            recs_list.append({
                'artist_name': row['artist_name'],
                'artist_url': row['artist_url'],
                'artist_wiki_url': 'https://'+row['wikipedia']
            })
        return recs_list
    
    def get_random_content(self, user_actions: List[Dict[str, str]], eps: float = 0.3) -> dict:
        print(user_actions)
        # bandit logic - main part. Choose tag on first stage, then choose content
        if np.random.random() < eps or len(user_actions) == 0:
            random_tag = np.random.choice(self.tags_df['tag'])
        else:
            tag_candidates = user_tags_ranking(user_actions, self.tags_df)['tag'].values
            random_tag = np.random.choice(tag_candidates)
        logger.info('random tag: %s', random_tag)
        res = int(np.random.choice(
            self.df[
                self.df['art_tags']  # artist_movement
                .apply(lambda x: random_tag in x.lower() if isinstance(x, str) else False)
            ].index
        ))
        return {'item_id': res, 'item_tag': random_tag}

class UserDB:
    def __init__(self):
        self.mongo = None
        self.user_actions = None
    
    def init_db(self):
        self.mongo = MongoClient(f'mongodb://{MONGO_HOST}:27017/')
        self.user_actions = self.mongo['artswipe_db']['user_actions']
    
    def get_user_actions(self, user_name: str) -> Tuple[str, List[Dict]]:
        # TODO: add cache
        user_activity = self.user_actions.find_one({'name': user_name})
        if user_activity is None:
            return None, None
        else:
            return str(user_activity['_id']), user_activity['actions']

    def create_user(self, user_name: str) -> str:
        user_id, _ = self.get_user_actions(user_name)
        if user_id is None:
            user_id = (
                self.user_actions
                .insert_one({'name': user_name, 'actions': []})
                .inserted_id
            )
        else:
            logger.info('User already exists')
        return str(user_id)

    def push_action(self, user_id: str, content_id: str, content_tag: str, action_type: str) -> str:
        action = {'content_id': content_id, 'content_tag': content_tag,'action': action_type}
        self.user_actions.update_one({'_id': ObjectId(user_id)}, {'$push': {'actions': action}})
        return True

