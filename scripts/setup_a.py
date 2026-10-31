"""Create a local .env without overwriting an existing file or printing secrets."""
import argparse
import secrets
from shared.config import ROOT

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite-preview', action='store_true', help='UI/chat preview only; the lab requires MySQL')
    args = parser.parse_args()
    target = ROOT/'.env'
    if target.exists():
        print('Existing .env retained. Edit its configuration locally.'); return
    password = secrets.token_urlsafe(24)
    content = (ROOT/'.env.example').read_text(encoding='utf-8')
    content = content.replace('please_change_me_to_a_long_random_value', secrets.token_urlsafe(48))
    content = content.replace('REGISTRATION_CODE=\n', f'REGISTRATION_CODE={secrets.token_urlsafe(24)}\n')
    content = content.replace('chatuser:CHANGE_ME@127.0.0.1:3306', f'chatuser:{password}@127.0.0.1:13306')
    content = content.replace('LAB9_MYSQL_PASSWORD=\n', f'LAB9_MYSQL_PASSWORD={password}\n')
    content = content.replace('LAB9_MYSQL_ROOT_PASSWORD=\n', f'LAB9_MYSQL_ROOT_PASSWORD={secrets.token_urlsafe(32)}\n')
    if args.sqlite_preview:
        (ROOT/'artifacts').mkdir(exist_ok=True)
        content = '\n'.join('DATABASE_URL=sqlite+aiosqlite:///'+(ROOT/'artifacts/preview.sqlite').as_posix()
                            if line.startswith('DATABASE_URL=') else line for line in content.splitlines())+'\n'
    with target.open('x', encoding='utf-8', newline='\n') as output:
        output.write(content)
    print('Created .env with local random secrets. Add your OpenAI key locally; start MySQL and Llama before asking the assistant.')

if __name__ == '__main__': main()
