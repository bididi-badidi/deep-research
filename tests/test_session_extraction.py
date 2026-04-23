from utils import get_session_id_by_prompt

def test_extraction():
    # The prompt I used at the start of this session:
    # "im focusing on gemini cli. is there any way to extract the gemini session"
    prompt = "im focusing on gemini cli. is there any way to extract the gemini session"
    project_name = "deep-research"
    
    session_id = get_session_id_by_prompt(project_name, prompt, n=20)
    
    if session_id:
        print(f"SUCCESS: Found session ID: {session_id}")
    else:
        print("FAILURE: Session ID not found.")

if __name__ == "__main__":
    test_extraction()
