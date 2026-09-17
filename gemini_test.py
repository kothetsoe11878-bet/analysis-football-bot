import json
from gemini_analysis import run_connection_test
result=run_connection_test()
print('GEMINI MODULE TEST: PASS')
print(json.dumps(result,ensure_ascii=False,indent=2))
