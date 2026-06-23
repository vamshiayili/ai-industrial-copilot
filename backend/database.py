import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DB_PATH

Base = declarative_base()
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    filepath = Column(String)
    doc_type = Column(String, index=True) # "manual", "regulation", "drawing", "incident"
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index = Column(Integer)
    content = Column(Text)
    page_number = Column(Integer, nullable=True)
    embedding_json = Column(Text, nullable=True) # JSON representation of the float vector

class Relation(Base):
    __tablename__ = "relations"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    target = Column(String, index=True)
    rel_type = Column(String, index=True) # "uses", "maintains", "references", "controls", "located_in"
    description = Column(Text)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

class IncidentLog(Base):
    __tablename__ = "incident_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    asset_id = Column(String, index=True) # e.g. "Compressor-05", "Boiler-101"
    hazard_description = Column(Text)
    lessons_learned = Column(Text)
    safety_precaution = Column(Text)
    severity = Column(String) # "High", "Medium", "Low"
    recorded_at = Column(DateTime, default=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String) # "user", "assistant"
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed default incidents if none exist
        if db.query(IncidentLog).count() == 0:
            default_incidents = [
                IncidentLog(
                    title="Compressor Seal Failure & Gas Leak",
                    asset_id="Compressor-05",
                    hazard_description="Maintenance technician attempted to replace dynamic O-ring seals on Compressor-05 while the nearby Boiler-101 was operating at full pressure (25 bar). A pressure surge in the compressor caused a seal blowout, venting flammable hydrocarbon gas. The high temperature from Boiler-101 acted as an ignition source, causing a localized flash fire.",
                    lessons_learned="Never perform hot seals maintenance on compressors while boilers or ignition sources within a 15-meter radius are active. Isolate gas feeds completely before seal disassembly.",
                    safety_precaution="Perform absolute pressure relief (depressurize to 0 bar), lock-out/tag-out (LOTO) on gas inlet valves, shut down and cool adjacent heat sources (e.g., Boiler-101), and set up continuous gas monitoring.",
                    severity="High"
                ),
                IncidentLog(
                    title="Boiler-101 Overheating and Valve Lockup",
                    asset_id="Boiler-101",
                    hazard_description="Scale accumulation inside the feed-water pipe of Boiler-101 caused a localized hotspot, leading to thermal expansion and locking the main steam safety valve (SV-101) in the closed position. This caused pressure to rise to critical limits.",
                    lessons_learned="Conduct scale cleaning (descaling) every 6 months. Maintain auxiliary cooling loops in a stand-by, ready state.",
                    safety_precaution="Verify SV-101 manual override functionality before cold startup. Install double block-and-bleed valve configuration on feed-water lines.",
                    severity="High"
                ),
                IncidentLog(
                    title="Pump-A Thermal Runaway and Cavitation",
                    asset_id="Pump-A",
                    hazard_description="Running Pump-A against a closed discharge valve during priming led to fluid recirculation, rapid temperature rise, vaporization of the process liquid, and severe impeller cavitation, which destroyed the mechanical seal.",
                    lessons_learned="Implement automatic thermal shutdown interlocks. Ensure suction and discharge valves are confirmed open before motor start.",
                    safety_precaution="Always check discharge valve path availability. Confirm pressure gauges are calibrated and operational.",
                    severity="Medium"
                ),
                IncidentLog(
                    title="Electrical Substation Arc Flash",
                    asset_id="Substation-02",
                    hazard_description="Technician opened Substation-02 panel door without verifying isolation or wearing rated Arc Flash PPE. Dust accumulation inside the busbar chamber triggered a line-to-ground flashover.",
                    lessons_learned="Implement high-voltage isolation checklist. Mandate Category 4 Arc Flash protection gear for panel opening.",
                    safety_precaution="De-energize feed lines, verify zero voltage via insulated probe, clean dust using non-conductive vacuums.",
                    severity="High"
                )
            ]
            db.add_all(default_incidents)
            
        # Seed default graph relationships for visualization and search
        if db.query(Relation).count() == 0:
            default_relations = [
                Relation(source="Boiler-101", target="Substation-02", rel_type="uses", description="Boiler control panel powered by Substation-02."),
                Relation(source="Compressor-05", target="Boiler-101", rel_type="located_in", description="Compressor-05 sits directly adjacent to Boiler-101 (within 10m safety zone)."),
                Relation(source="Pump-A", target="Boiler-101", rel_type="controls", description="Pump-A supplies feedwater directly to Boiler-101."),
                Relation(source="Maintenance Team A", target="Compressor-05", rel_type="maintains", description="Assigned primary preventive maintenance duties for Compressor-05."),
                Relation(source="OSHA-Standard-1910", target="Boiler-101", rel_type="references", description="Boiler-101 pressure vessels must adhere to OSHA 1910.106 guidelines."),
                Relation(source="OSHA-Standard-1910", target="Compressor-05", rel_type="references", description="Compressor safety interlocks audited under OSHA 1910.147 (LOTO)."),
                Relation(source="PESO-Regulation-2024", target="Compressor-05", rel_type="references", description="Venting valves must be compliant with PESO gas cylinders regulations.")
            ]
            db.add_all(default_relations)
            
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
