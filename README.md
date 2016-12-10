# Description

Simple Web Scrapping tool to get my data from [MyNetDiary](https://www.mynetdiary.com/)

This is a Python based project and it uses pip (via `requirements.txt`) to track dependencies.

I am currently running it (as most of my Python projects) via Virtualenv and the direnv integration in macOS.

It is kept simple enough, with embedded credentials (until I modify it a bit, but will I?).

# Configuration

Copy the `credentials.example.yaml` file into a `credentials.yaml` and modify it to configure your own username and password in [MyNetDiary](https://www.mynetdiary.com/).

Execute `python webscrapping.py` to generated an `output.csv` result file with dates and weights.

You'll probably need to install the dependencies, which are described in `requirements.txt`. The simplest way is using `pip install -r requirements` on an isolated Virtualenv environment, but feel free to adapt this process as you fancy.

Currently, the process takes less than a minute for a span of 4 years, which is way better than doing it by hand. By default, the start date is `2012-01-01`. This is not configurable or based on an argument to keep it simple and because I don't want to spend more time than needed on this script, but feel free to edit the `webscrapping.py` file (replacing the value of the `startDate` variable with a year-month-day format).
