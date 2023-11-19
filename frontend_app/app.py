"""
----------------------------
Visualization app on Streamlit
----------------------------
"""
import logging
import os
from typing import Dict, Optional

import requests
import streamlit as st

class APIClient:
    def __init__(self):
        self.url = 'http://bandit_container:8090/'

    def get(self, endpoint: str, params: Optional[Dict[str, str]] = None, num_retries = 10) -> str:
        for _ in range(num_retries):
            try:
                resp = requests.get(os.path.join(self.url, endpoint), json=params)
                return resp.json()
            except requests.exceptions.ConnectionError as e:
                logger.error('%s\n%s', endpoint, e)
            except requests.exceptions.JSONDecodeError as e:
                logger.error('%s\n%s', endpoint, e)

    def post(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> str:
        resp = requests.post(os.path.join(self.url, endpoint), json=params)
        return resp.json()

api_client = APIClient()
logger = logging.getLogger('my_logger')
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)

def do_action(action_type: str, item_id: int, tag: str, user_token: str, user_name: str):
    if action_type in ('like', 'dislike'):
        action_context = {'item_id': item_id, 'action_type': action_type, 'user_token': user_token, 'user_name': user_name, 'item_tag': tag}
        api_client.post('action', params=action_context)

def request_random_artist_json() -> Dict:
    res = {}
    random_content = api_client.post('random', params={'user_name': st.session_state['user_name']})
    artist_id = random_content['item_id']
    artist_tag = random_content['item_tag']
    logger.info('random artist: %d', artist_id)
    res = api_client.get(f'items/{artist_id}')
    res.update({'tag': artist_tag})
    return res

def main():
    app_formal_name = "Swipe an artist"
    st.set_page_config(
        layout="wide", page_title=app_formal_name,
    )

    title_element = st.empty()
    title_element.title("Swipe an artist!")

    if not 'session_started' in st.session_state.keys():
        auth_button = st.button('Start session 🚀')
    if 'session_started' not in st.session_state.keys() and auth_button:
        user_name = api_client.get('user_name')['user_name']
        user_token = api_client.post('auth', params={'user_name': user_name})['Bearer']
        st.session_state['session_started'] = True
        st.session_state['user_token'] = user_token
        st.session_state['user_name'] = user_name
        st.session_state['content_count'] = 0
        logger.info('Session start for %s', user_name)
    
    NUM_IMPRESSIONS = 5
    
    if 'session_started' in st.session_state.keys() and st.session_state['session_started'] is True:
        if st.session_state['content_count'] == NUM_IMPRESSIONS:
            user_data = {'user_name': st.session_state['user_name']}
            res = api_client.post('recommend', params=user_data)['recs']
            st.write('We recommend you based on your likes')
            for rec in res:
                link_text = rec['artist_name']
                link_url = rec['artist_url']
                link_markdown = f"[{link_text}]({link_url})"
                st.markdown(link_markdown, unsafe_allow_html=True)
        else:
            st.session_state['content_count'] = st.session_state['content_count'] + 1
            user_name = st.session_state['user_name']
            user_token = st.session_state['user_token']  # exists for sure because session is already started
            random_artist = request_random_artist_json()
            artist_id = random_artist['item']['artist_id']
            col1, col2, col3 = st.columns([1, 2, 1], gap='large')
            with col1:
                like_button = st.button('🤩')
            with col2:
                st.write('%d of %d' % (st.session_state['content_count'], NUM_IMPRESSIONS))
            with col3:
                dislike_button = st.button('🥴')
            if like_button:
                do_action('like', artist_id, random_artist['tag'], user_token, user_name)
            if dislike_button:
                do_action('dislike', artist_id, random_artist['tag'], user_token, user_name)

            st.image(random_artist['item']['artworks'], caption=random_artist['item']['artwork_name'])
            st.write(f"""[{random_artist['item']['artist_name']}]({random_artist['item']['artist_url']}), {random_artist['item']['field']}, {random_artist['item']['artist_movement']}""")

if __name__ == '__main__':
    main()