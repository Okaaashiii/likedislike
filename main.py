from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# --- Database configuration ---
db_config = {
    'host': 'localhost',
    'user': 'your_user',        # Replace with your MySQL username
    'password': 'your_password',# Replace with your MySQL password
    'database': 'your_database' # Replace with your MySQL database
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- Record Recruiter Feedback ---
@app.route('/feedback', methods=['POST'])
def record_feedback():
    data = request.json
    candidate_id = data.get('candidate_id')
    vote_type = data.get('vote_type')  # 'like' or 'dislike'

    if not candidate_id or vote_type not in ['like', 'dislike']:
        return jsonify({'error': 'Invalid candidate_id or vote_type'}), 400

    liked_value = (vote_type == 'like')  # Convert 'like' to True, 'dislike' to False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Update the liked field
        cursor.execute("""
            UPDATE JobCandidateViews
            SET liked = %s
            WHERE candidate_id = %s
        """, (liked_value, candidate_id))

        if cursor.rowcount == 0:
            return jsonify({'error': 'Candidate not found in JobCandidateViews'}), 404

        # 2. Update CandidateRelevanceCounter safely
        if liked_value:
            cursor.execute("""
                UPDATE CandidateRelevanceCounter
                SET likes_count = likes_count + 1
                WHERE candidate_id = %s
            """, (candidate_id,))
        else:
            cursor.execute("""
                UPDATE CandidateRelevanceCounter
                SET dislikes_count = dislikes_count + 1
                WHERE candidate_id = %s
            """, (candidate_id,))

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
    candidate_id = request.args.get('candidate_id')

    if not candidate_id:
        return jsonify({'error': 'Missing candidate_id'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                GREATEST(likes_count, 0) AS safe_likes, 
                GREATEST(dislikes_count, 0) AS safe_dislikes
            FROM CandidateRelevanceCounter
            WHERE candidate_id = %s
        """, (candidate_id,))

        result = cursor.fetchone()
        likes, dislikes = result if result else (0, 0)

        return jsonify({
            'candidate_id': candidate_id,
            'likes': likes,
            'dislikes': dislikes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# --- Main ---
if __name__ == '__main__':
    app.run(debug=True)
