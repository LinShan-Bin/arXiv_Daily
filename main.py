import os
import sys
import time
import pytz
from datetime import datetime
from openai import OpenAI

from utils import get_daily_papers_by_keyword, generate_table, back_up_files,\
    restore_files, remove_backups, get_daily_date


client = OpenAI(
    api_key = os.environ.get("ARK_API_KEY"),
    base_url = "https://ark.cn-beijing.volces.com/api/v3",
)


beijing_timezone = pytz.timezone('Asia/Shanghai')

# NOTE: arXiv API seems to sometimes return an unexpected empty list.

# get current beijing time date in the format of "2021-08-01"
current_date = datetime.now(beijing_timezone).strftime("%Y-%m-%d")
# get last update date from README.md
with open("README.md", "r") as f:
    while True:
        line = f.readline()
        if "Last update:" in line: break
    last_update_date = line.split(": ")[1].strip()
    # if last_update_date == current_date:
        # sys.exit("Already updated today!")

keywords = ["3D", "robo", "reconstruction", "manipulation", "grasping", "embodied", \
            "navigation", "reasoning", "diffusion", "language model", "cot", "vision language action"]

max_result = 100 # maximum query results from arXiv API for each keyword
issues_result = 15 # maximum papers to be included in the issue

# all columns: Title, Authors, Abstract, Link, Tags, Comment, Date
# fixed_columns = ["Title", "Link", "Date"]

column_names = ["Title", "Link", "Abstract", "Date", "Comment"]

back_up_files() # back up README.md and ISSUE_TEMPLATE.md

# write to README.md
f_rm = open("README.md", "w") # file for README.md
f_rm.write("# Daily Papers\n")
f_rm.write("The project automatically fetches the latest papers from arXiv based on keywords.\n\nThe subheadings in the README file represent the search keywords.\n\nOnly the most recent articles for each keyword are retained, up to a maximum of 100 papers.\n\nYou can click the 'Watch' button to receive daily email notifications.\n\nLast update: {0}\n\n".format(current_date))

# write to ISSUE_TEMPLATE.md
f_is = open(".github/ISSUE_TEMPLATE.md", "w") # file for ISSUE_TEMPLATE.md
f_is.write("---\n")
f_is.write("title: Latest {0} Papers - {1}\n".format(issues_result, get_daily_date()))
f_is.write("labels: documentation\n")
f_is.write("---\n")
f_is.write("**Please check the [Github](https://github.com/LinShan-Bin/Daily_arXiv) page for a better reading experience and more papers.**\n\n")

paper_list = []
for _ in range(3):  # try 3 times
    for keyword in keywords:
        link = "OR"
        papers = get_daily_papers_by_keyword(keyword, column_names, max_result, link)
        if papers is not None:
            paper_list.extend(papers)
        time.sleep(5) # avoid being blocked by arXiv API
    if len(paper_list) > 0:
        break
    time.sleep(60 * 30)

print("Total papers: ", len(paper_list))
print("paper 0: ", paper_list[0])

if len(paper_list) == 0: # failed to get papers
    print("Failed to get papers!")
    f_rm.close()
    f_is.close()
    restore_files()
    sys.exit("Failed to get papers!")

for paper in paper_list:
    for _ in range(3):  # try 3 times
        try:
            completion = client.chat.completions.create(
                model = "doubao-1-5-lite-32k-250115",  # your model endpoint ID
                messages = [
                    {"role": "system", "content": "你是人工智能助手，请你根据论文标题及摘要用100字以内中文简要总结下面的论文。主要关注论文做了什么、有何创新点。"},
                    {"role": "user", "content": f"{paper['Title']}\n{paper['Abstract']}"},
                ],
            )
            break
        except Exception as e:
            time.sleep(30)

    print(completion.choices[0].message.content)
    paper["Summary"] = completion.choices[0].message.content

rm_table = generate_table(paper_list)
is_table = generate_table(paper_list[:issues_result], ignore_keys=["Abstract", "Summary"])
f_rm.write(rm_table)
f_rm.write("\n\n")
f_is.write(is_table)
f_is.write("\n\n")

f_rm.close()
f_is.close()
remove_backups()
