import streamlit as st
from github import Github, GithubException, Auth
from requests import RequestException
from datetime import datetime
import plotly.graph_objects as go
import os
from policyengine_core.charts import format_fig
import backoff


@backoff.on_exception(
    backoff.constant,
    (GithubException, RequestException),
    jitter=None,
    interval=2,
    max_tries=5,
)
def count_merged_pull_requests(
    g, org, start_date, end_date, breakdown_by_repo
):
    total_merged = 0
    merged_count = {}

    if breakdown_by_repo:
        org = g.get_organization(org)
        repos = org.get_repos()
        total_repos = repos.totalCount
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, repo in enumerate(repos):
            query = f"is:pr is:merged merged:{start_date}..{end_date} repo:{org.login}/{repo.name}"
            results = g.search_issues(query)
            count = results.totalCount
            if count > 0:
                merged_count[repo.name] = count
            total_merged += count

            progress = (i + 1) / total_repos
            progress_bar.progress(progress)
            status_text.text(f"Processing repository {i + 1} of {total_repos}")

        status_text.text("Processing complete!")
    else:
        query = f"is:pr is:merged merged:{start_date}..{end_date} org:{org}"
        results = g.search_issues(query)
        total_merged = results.totalCount

    return total_merged, merged_count


def main():
    st.set_page_config(page_title="GitHub Merged Pull Requests", layout="wide")
    st.title("GitHub Merged Pull Requests")

    access_token = os.getenv(
        "GITHUB_ACCESS_TOKEN", st.secrets["GITHUB_ACCESS_TOKEN"]
    )
    auth = Auth.Token(access_token)
    g = Github(auth=auth)

    org = st.text_input(
        "Enter the GitHub organization name:", value="PolicyEngine"
    )

    current_year = datetime.now().year
    start_date = st.date_input(
        "Select the start date:",
        value=datetime(current_year, 1, 1),
        format="YYYY-MM-DD",
    )
    end_date = st.date_input(
        "Select the end date:", value=datetime.now(), format="YYYY-MM-DD"
    )

    breakdown_by_repo = st.checkbox("Break down by repository", value=True)

    if st.button("Count Merged Pull Requests"):
        if org and access_token:
            try:
                total_merged, merged_prs = count_merged_pull_requests(
                    g,
                    org,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    breakdown_by_repo,
                )

                st.write(f"Total Merged Pull Requests: {total_merged}")

                if breakdown_by_repo:
                    sorted_merged_prs = sorted(
                        merged_prs.items(), key=lambda x: x[1], reverse=False
                    )
                    repos = [item[0] for item in sorted_merged_prs]
                    counts = [item[1] for item in sorted_merged_prs]

                    fig = go.Figure(
                        data=[go.Bar(y=repos, x=counts, orientation="h")]
                    )
                    fig.update_layout(
                        title=f"Merged Pull Requests by Repository for {org} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
                        xaxis_title="Number of Merged Pull Requests",
                        yaxis_title="Repository",
                        height=600,
                    )

                    st.plotly_chart(format_fig(fig), use_container_width=True)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning(
                "Please provide the organization name and access token."
            )

    g.close()


if __name__ == "__main__":
    main()
