"""Bounded EKLAVYA load journeys. Always point this at disposable infrastructure."""

from uuid import uuid4

from locust import HttpUser, between, task


class BrowsingUser(HttpUser):
    weight = 4
    wait_time = between(0.2, 1.0)

    @task(4)
    def catalog(self):
        self.client.get("/api/v1/problems?limit=50", name="GET catalog")

    @task(2)
    def problem(self):
        self.client.get("/api/v1/problems/parity-check", name="GET problem")

    @task
    def leaderboard(self):
        self.client.get("/api/v1/gamification/leaderboard?limit=50", name="GET leaderboard")

    @task
    def contest_standings(self):
        contests = self.client.get("/api/v1/contests", name="GET contests")
        if contests.ok and contests.json():
            slug = contests.json()[0]["slug"]
            self.client.get(f"/api/v1/contests/{slug}/leaderboard", name="GET contest standings")


class SubmissionUser(HttpUser):
    weight = 1
    wait_time = between(1.0, 2.0)

    def on_start(self):
        suffix = uuid4().hex[:12]
        response = self.client.post("/api/v1/auth/register", json={
            "email": f"load-{suffix}@example.com", "username": f"load_{suffix}",
            "password": "BoundedLoad123", "display_name": "Load Test User",
        }, name="POST register")
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"} if response.ok else {}
        self.submission_id = None

    @task(2)
    def submission_history(self):
        self.client.get("/api/v1/submissions?limit=10", headers=self.headers, name="GET submission history")

    @task
    def submit_and_poll(self):
        response = self.client.post("/api/v1/problems/parity-check/submissions", headers=self.headers, json={
            "language": "python", "source_code": "n=int(input())\nprint('Even' if n%2==0 else 'Odd')",
            "mode": "SUBMIT",
        }, name="POST submission")
        if response.status_code == 202:
            self.submission_id = response.json()["id"]
            self.client.get(
                f"/api/v1/submissions/{self.submission_id}", headers=self.headers,
                name="GET submission status",
            )
