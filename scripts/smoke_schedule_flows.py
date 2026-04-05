import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import User


def main():
    app = create_app()
    app.config['TESTING'] = True

    output = {
        'ok': True,
        'results': []
    }

    with app.test_client() as client:
        login_get = client.get('/login')
        output['results'].append({
            'step': 'GET /login',
            'status': login_get.status_code,
            'content_type': login_get.content_type,
        })

        html = login_get.get_data(as_text=True)
        match = re.search(r'name="csrf_token"\s+type="hidden"\s+value="([^"]+)"', html)
        if not match:
            output['ok'] = False
            output['error'] = 'CSRF token not found on login page'
            print(json.dumps(output, indent=2))
            return

        csrf_token = match.group(1)

        credential_candidates = [
            ('admin@ischedwise.com', 'admin123'),
            ('test@ischedwise.local', 'superadmin123'),
            ('dean@ischedwise.com', 'dean123'),
        ]

        login_post = None
        successful_credential = None
        for username, password in credential_candidates:
            login_post = client.post(
                '/login',
                data={
                    'csrf_token': csrf_token,
                    'username': username,
                    'password': password,
                    'remember': 'y',
                },
                follow_redirects=False,
            )

            # Successful login should not redirect back to /login.
            location = login_post.headers.get('Location', '')
            if login_post.status_code in (301, 302, 303, 307, 308) and not location.startswith('/login'):
                successful_credential = username
                break
        output['results'].append({
            'step': 'POST /login',
            'status': login_post.status_code,
            'location': login_post.headers.get('Location', ''),
            'credential_used': successful_credential,
        })

        if login_post.status_code in (301, 302, 303, 307, 308):
            target = login_post.headers.get('Location', '/main/dashboard')
            redirect_get = client.get(target)
            output['results'].append({
                'step': f'GET {target}',
                'status': redirect_get.status_code,
                'content_type': redirect_get.content_type,
            })

        # If auth is still not established in this local test context,
        # force a valid session user for endpoint smoke checks.
        if successful_credential is None:
            with app.app_context():
                fallback_user = User.query.filter_by(is_active=True).first()
            if fallback_user:
                with client.session_transaction() as session_data:
                    session_data['_user_id'] = str(fallback_user.id)
                    session_data['_fresh'] = True
                output['results'].append({
                    'step': 'SESSION AUTH FALLBACK',
                    'user_id': fallback_user.id,
                    'username': getattr(fallback_user, 'username', None),
                })
            else:
                output['ok'] = False
                output['error'] = 'No active fallback user found for session auth'
                print(json.dumps(output, indent=2))
                return

        class_page = client.get('/schedule/class')
        exam_page = client.get('/schedule/exam')

        output['results'].append({
            'step': 'GET /schedule/class',
            'status': class_page.status_code,
            'content_type': class_page.content_type,
        })
        output['results'].append({
            'step': 'GET /schedule/exam',
            'status': exam_page.status_code,
            'content_type': exam_page.content_type,
        })

        valid_curr = client.get('/schedule/get-curricula/32')
        invalid_curr = client.get('/schedule/get-curricula/999999')

        output['curricula_valid'] = {
            'status': valid_curr.status_code,
            'content_type': valid_curr.content_type,
            'is_json': valid_curr.content_type.startswith('application/json'),
            'body_sample': valid_curr.get_data(as_text=True)[:240],
        }
        output['curricula_invalid'] = {
            'status': invalid_curr.status_code,
            'content_type': invalid_curr.content_type,
            'is_json': invalid_curr.content_type.startswith('application/json'),
            'body': invalid_curr.get_data(as_text=True),
        }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
