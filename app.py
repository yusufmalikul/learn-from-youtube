import argparse
import random
from googleapiclient.discovery import build
import isodate
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
import pytz
import json

def youtube_search(api_key, search_term, topic_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.search().list(
        part='snippet',
        maxResults=50,
        q=search_term,
        topicId=topic_id,
        type='video',
        relevanceLanguage='en,id'  # Add this line to filter by English and Indonesian
    )
    response = request.execute()
    video_ids = [item['id']['videoId'] for item in response['items'] if item['id']['kind'] == 'youtube#video']
    return video_ids

def get_top_comments(api_key, video_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.commentThreads().list(
        part='snippet',
        videoId=video_id,
        maxResults=3,
        order='relevance'
    )
    response = request.execute()
    comments = []
    for item in response['items']:
        comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
        comments.append(comment)
    return comments

def get_video_details(api_key, video_ids):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.videos().list(
        part='statistics,snippet,contentDetails,topicDetails,status',
        id=','.join(video_ids)
    )
    response = request.execute()
    total_videos = len(response['items'])
    print(f"Total videos: {total_videos}")
    video_details = {}
    for item in response['items']:
        video_id = item['id']
        statistics = item.get('statistics', {})
        snippet = item['snippet']
        content_details = item['contentDetails']
        topic_details = item.get('topicDetails', {})
        published_at = parser.parse(snippet['publishedAt'])
        status = item.get('status', {})
        now = datetime.now(pytz.utc)
        delta = relativedelta(now, published_at)
        if delta.years > 0:
            published_at_str = f"{delta.years} years ago"
        elif delta.months > 0:
            published_at_str = f"{delta.months} months ago"
        elif delta.days > 0:
            published_at_str = f"{delta.days} days ago"
        elif delta.hours > 0:
            published_at_str = f"{delta.hours} hours ago"
        elif delta.minutes > 0:
            published_at_str = f"{delta.minutes} minutes ago"
        else:
            published_at_str = "just now"
        video_details[video_id] = {
            'title': snippet['title'],
            'view_count': statistics.get('viewCount', 'N/A'),
            'like_count': statistics.get('likeCount', 'N/A'),
            'comment_count': statistics.get('commentCount', 'N/A'),
            'published_at': published_at_str,
            'thumbnail_url': snippet['thumbnails']['default']['url'],
            'duration': format_duration(content_details['duration']),
            'topic_categories': [url.split('/')[-1] for url in topic_details.get('topicCategories', [])],
            'is_short': isodate.parse_duration(content_details['duration']).total_seconds() <= 60,
            'made_for_kids': status.get('madeForKids', False),
            'top_comments': get_top_comments(api_key, video_id) if int(statistics.get('commentCount', 0)) > 0 else []
        }
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))
        if view_count > 0:
            like_view_ratio = (like_count / view_count) * 100
            video_details[video_id]['like_view_ratio'] = f"{like_view_ratio:.2f}%"
        else:
            video_details[video_id]['like_view_ratio'] = '0.00%'

    video_details = {video_id: details for video_id, details in video_details.items() if not details['is_short']}
    return video_details

def format_duration(duration):
    parsed_duration = isodate.parse_duration(duration)
    total_seconds = int(parsed_duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def main():
    parser = argparse.ArgumentParser(description='YouTube Video Search CLI')
    parser.add_argument('--topic', type=str, help='Topic to search for (lifestyle, hobby, knowledge)')
    parser.add_argument('--api-key', type=str, required=True, help='Your YouTube Data API v3 key')
    parser.add_argument('--output', type=str, default='videos.json', help='Output JSON file name (default: videos.json)')

    args = parser.parse_args()

    topic_ids = {
        'lifestyle': '/m/019_rr',
        'hobby': '/m/03glg',
        'knowledge': '/m/01k8wb',
        'technology': '/m/07c1v',
        'business': '/m/09s1f',
        'health': '/m/0kt51',
    }

    if not args.topic:
        args.topic = random.choice(list(topic_ids.keys()))
        print(f"No topic provided. Randomly selected topic: {args.topic}")

    topic_id = topic_ids.get(args.topic)
    if not topic_id:
        print(f"Error: Invalid topic. Choose from: {', '.join(topic_ids.keys())}")
        return

    search_term = " "
    video_ids = youtube_search(args.api_key, search_term, topic_id)
    if video_ids:
        video_details = get_video_details(args.api_key, video_ids)
        if video_details:
            try: # try to load existing json
                with open(args.output, 'r') as f:
                    existing_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError): # if file not exist or not valid json, create empty dict
                existing_data = {}

            # Update with new video details, this will append because dict keys will be updated, not overwritten if keys are different
            existing_data.update(video_details)

            with open(args.output, 'w') as f:
                json.dump(existing_data, f, indent=4)
            print(f"Video details appended to {args.output}") # message changed to appended
        else:
            print("No video details found.")
    else:
        print("No videos found.")

if __name__ == '__main__':
    main()