# --- Importe ---
# Hier werden alle notwendigen Bibliotheken und Klassen importiert.
# Eine saubere Gruppierung hilft, den Überblick zu behalten.
from fastapi import FastAPI, Path, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn

# --- App-Initialisierung ---
# Dies ist die zentrale Instanz deiner FastAPI-Anwendung.
# Alle API-Routen ("Endpoints") werden über dieses 'app'-Objekt registriert.
app = FastAPI()


# --- Datenmodelle (Pydantic Schemas) ---
# Pydantic-Modelle sind das Herzstück der Datenvalidierung in FastAPI.
# Sie definieren eine klare Struktur (ein "Schema") für die JSON-Daten,
# die deine API erwartet (Request) und zurückgibt (Response).
# Dies dient als "Single Source of Truth" für deine Datenstrukturen.

class Item(BaseModel):
    """
    Definiert die erwartete Struktur für den Request Body beim Erstellen
    oder Aktualisieren eines Items. Man nennt dies auch ein Data Transfer Object (DTO).
    """
    # Field(...) macht ein Feld erforderlich und erlaubt zusätzliche Validierungsregeln.
    name: str = Field(..., min_length=3, max_length=50, description="Name des Items (zwischen 3 und 50 Zeichen).")
    price: float = Field(..., gt=0, description="Preis des Items (muss größer als 0 sein).")
    is_offer: Optional[bool] = None


class ItemResponse(BaseModel):
    """
    Definiert die Struktur der Daten, die an den Client zurückgesendet werden.
    Es ist eine Best Practice, separate Modelle für Requests und Responses zu haben.
    So kannst du steuern, welche Daten nach außen sichtbar sind (z.B. die ID hinzufügen,
    aber interne Felder oder Passwörter weglassen).
    """
    id: int
    name: str
    price: float


# --- Mock-Datenbank ---
# Dies ist eine einfache In-Memory-Liste, die eine Datenbank simuliert.
# In einer echten Anwendung würde hier die Logik zur Interaktion mit einer
# echten Datenbank (z.B. PostgreSQL, MongoDB) über ein ORM wie SQLAlchemy stehen.
fake_items_db = [
    {"id": 1, "name": "Foo", "price": 50.5},
    {"id": 2, "name": "Bar", "price": 65.2},
    {"id": 3, "name": "Baz", "price": 19.99},
]


# --- API-Endpunkte (Routen) ---

@app.get("/")
async def root():
    """
    Ein einfacher GET-Endpunkt für die Stamm-URL.
    Wird oft für einen "Health Check" verwendet, um zu prüfen, ob der Dienst online ist.
    """
    return {"message": "Hello World"}


@app.get("/items/", response_model=List[ItemResponse])
async def read_items(skip: int = 0, limit: int = 10):
    """
    Ruft eine Liste von Items ab. Unterstützt Paginierung über Query-Parameter.
    - `skip` & `limit` sind Query-Parameter mit Standardwerten.
      URL-Beispiel: /items/?skip=0&limit=5
    - `response_model` ist entscheidend: Es stellt sicher, dass die Antwort dem
      `ItemResponse`-Schema entspricht. Das schützt vor dem versehentlichen
      Leaken von internen Daten und garantiert einen stabilen API-Vertrag.
    """
    return fake_items_db[skip : skip + limit]


@app.get("/items/{item_id}", response_model=ItemResponse)
async def read_item(item_id: int = Path(..., description="The ID of the item to get.", gt=0)):
    """
    Ruft ein einzelnes Item anhand seiner ID ab.
    - `{item_id}` ist ein Pfad-Parameter, da er Teil der URL-Struktur ist.
    - `Path(...)` fügt erweiterte Validierung und Dokumentation für den Pfad-Parameter hinzu.
    - Wenn das Item nicht gefunden wird, wird eine saubere HTTP-404-Antwort ausgelöst.
      Dies ist professionelles Fehler-Handling.
    """
    # Die 'next'-Funktion mit einem Generator-Ausdruck ist die effizienteste
    # Methode in Python, um das *erste* passende Element in einer Sequenz zu finden.
    # Die Suche stoppt, sobald ein Treffer gefunden wird. Der zweite Parameter (None)
    # ist der Standardwert, der zurückgegeben wird, wenn nichts gefunden wird.
    item = next((item for item in fake_items_db if item["id"] == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item_update: Item):
    """
    Aktualisiert ein bestehendes Item. Die PUT-Methode impliziert ein
    vollständiges Ersetzen der Ressource durch die neuen Daten.
    - `item_update: Item` bedeutet, dass FastAPI den Request Body erwartet,
      ihn gegen das `Item`-Modell validiert und als Objekt bereitstellt.
    """
    # In einer echten DB würde man ein "UPDATE ... WHERE id=..." Statement ausführen.
    # Hier simulieren wir das, indem wir den Index in der Liste finden.
    index_to_update = -1
    for i, current_item in enumerate(fake_items_db):
        if current_item["id"] == item_id:
            index_to_update = i
            break

    # Sauberes Abfangen des "Nicht gefunden"-Falls.
    if index_to_update == -1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # .model_dump() konvertiert das Pydantic-Modell in ein Dictionary.
    updated_item_data = item_update.model_dump()
    updated_item_data["id"] = item_id
    fake_items_db[index_to_update] = updated_item_data
    return updated_item_data


@app.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    """
    Erstellt ein neues Item.
    - `item: Item`: FastAPI validiert den JSON-Payload automatisch. Bei Fehlern
      (z.B. Preis ist negativ) sendet es eine detaillierte 422-Fehlerantwort.
      Das erspart dir manuellen Validierungscode.
    - `status_code=status.HTTP_201_CREATED`: Setzt den HTTP-Statuscode für eine
      erfolgreiche Antwort explizit auf 201, was dem Standard für die
      Erstellung einer neuen Ressource entspricht.
    """
    # Simuliert die Generierung einer neuen, einzigartigen ID durch die Datenbank.
    new_id = max(i["id"] for i in fake_items_db) + 1
    new_item_data = item.model_dump()
    new_item_data["id"] = new_id
    fake_items_db.append(new_item_data)
    return new_item_data


if __name__ == "__main__":
    # Dieser Block wird nur ausgeführt, wenn das Skript direkt mit `python main.py`
    # gestartet wird. Er dient dem lokalen Entwickeln.
    # - `uvicorn.run(...)`: Startet den ASGI-Server, der deine App ausführt.
    # - `reload=True`: Ist extrem nützlich in der Entwicklung. Der Server startet
    #   automatisch neu, sobald du eine Änderung im Code speicherst.
    # In einer Produktionsumgebung würdest du den Server anders starten,
    # z.B. mit: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
    print("Starting FastAPI server... Go to http://127.0.0.1:8000/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)