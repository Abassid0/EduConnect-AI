from pydantic import BaseModel


class WhatsAppProfile(BaseModel):
    name: str


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile
    wa_id: str


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppInteractiveReply(BaseModel):
    id: str
    title: str
    description: str | None = None


class WhatsAppButtonReply(BaseModel):
    id: str
    title: str


class WhatsAppInteractive(BaseModel):
    type: str
    list_reply: WhatsAppInteractiveReply | None = None
    button_reply: WhatsAppButtonReply | None = None


class WhatsAppMessage(BaseModel):
    from_: str | None = None
    id: str | None = None
    timestamp: str | None = None
    type: str | None = None
    text: WhatsAppTextBody | None = None
    interactive: WhatsAppInteractive | None = None

    class Config:
        populate_by_name = True

    def __init__(self, **data: object) -> None:
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)

    @property
    def sender_number(self) -> str:
        return self.from_ or ""

    @property
    def user_input(self) -> str:
        if self.type == "text" and self.text:
            return self.text.body
        if self.type == "interactive" and self.interactive:
            if self.interactive.list_reply:
                return self.interactive.list_reply.id
            if self.interactive.button_reply:
                return self.interactive.button_reply.id
        return ""


class WhatsAppStatus(BaseModel):
    id: str
    status: str
    timestamp: str
    recipient_id: str


class WhatsAppMetadata(BaseModel):
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppMessage] | None = None
    statuses: list[WhatsAppStatus] | None = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]

    def extract_messages(self) -> list[tuple[WhatsAppMessage, WhatsAppContact | None]]:
        results: list[tuple[WhatsAppMessage, WhatsAppContact | None]] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue
                value = change.value
                contacts = {c.wa_id: c for c in (value.contacts or [])}
                for msg in value.messages or []:
                    contact = contacts.get(msg.sender_number)
                    results.append((msg, contact))
        return results

    def extract_statuses(self) -> list[WhatsAppStatus]:
        statuses: list[WhatsAppStatus] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue
                statuses.extend(change.value.statuses or [])
        return statuses
