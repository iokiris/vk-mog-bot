class User:
    uid: int
    access: int
    voice_config: str

    def __init__(self, user_id: int, access: int, voice_config: str):
        self.uid: int = user_id
        self.access: int = access
        self.voice_config: str = voice_config
