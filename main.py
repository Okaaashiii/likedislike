from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'your_user',
    'password': 'your_password',
    'database': 'your_database'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- Record Recruiter Feedback ---
@app.route('/feedback', methods=['POST'])
def record_feedback():
    data = request.json
    job_id = data.get('job_id')
    candidate_id = data.get('candidate_id')
    vote_type = data.get('vote_type')  # 'like' or 'dislike'
    note = data.get('feedback_note', '')

    if vote_type not in ['like', 'dislike']:
        return jsonify({'error': 'Invalid vote type'}), 400

    liked_value = (vote_type == 'like')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Insert or update JobCandidateViews
        cursor.execute("""
            INSERT INTO JobCandidateViews (job_id, candidate_id, shown_at, liked, feedback_note)
            VALUES (%s, %s, NOW(), %s, %s)
            ON DUPLICATE KEY UPDATE
                liked = VALUES(liked),
                feedback_note = VALUES(feedback_note)
        """, (job_id, candidate_id, liked_value, note))

        # 2. Update CandidateRelevanceCounter
        if liked_value:
            cursor.execute("""
                INSERT INTO CandidateRelevanceCounter (candidate_id, job_id, likes_count, dislikes_count)
                VALUES (%s, %s, 1, 0)
                ON DUPLICATE KEY UPDATE likes_count = likes_count + 1
            """, (candidate_id, job_id))
        else:
            cursor.execute("""
                INSERT INTO CandidateRelevanceCounter (candidate_id, job_id, likes_count, dislikes_count)
                VALUES (%s, %s, 0, 1)
                ON DUPLICATE KEY UPDATE dislikes_count = dislikes_count + 1
            """, (candidate_id, job_id))

        conn.commit()
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# --- Fetch Like/Dislike Counts ---
@app.route('/feedback/count', methods=['GET'])
def get_feedback_counts():
    job_id = request.args.get('job_id')
    candidate_id = request.args.get('candidate_id')

    if not job_id or not candidate_id:
        return jsonify({'error': 'Missing job_id or candidate_id'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT likes_count, dislikes_count
            FROM CandidateRelevanceCounter
            WHERE job_id = %s AND candidate_id = %s
        """, (job_id, candidate_id))

        result = cursor.fetchone()
        likes, dislikes = result if result else (0, 0)

        return jsonify({
            'job_id': job_id,
            'candidate_id': candidate_id,
            'likes': likes,
            'dislikes': dislikes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
