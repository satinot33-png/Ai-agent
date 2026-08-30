import os

class AIAgent:
    def __init__(self, name="Java Global AI Agent"):
        self.name = name

    def respond(self, message):
        return f"{self.name}: Saya menerima pesan: {message}"


if __name__ == "__main__":
    agent = AIAgent()
    print(agent.respond("Agent AI aktif"))
