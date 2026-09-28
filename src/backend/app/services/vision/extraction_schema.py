from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ClothingObservation(BaseModel):
    item_type: Optional[str] = Field(default=None, description="e.g. shirt, t-shirt, trousers, jeans, jacket, shoes")
    color: Optional[str] = Field(default=None, description="Color of clothing item e.g. blue, dark blue, white")
    pattern: Optional[str] = Field(default=None, description="Pattern e.g. solid, striped, floral, plaid")
    description: Optional[str] = Field(default=None, description="Full description of visible clothing e.g. blue collared shirt")
    status: str = Field(default="OBSERVED", description="OBSERVED, INFERRED, or UNKNOWN")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Model visual confidence in observation 0.0-1.0")
    notes: Optional[str] = None


class JewelleryObservation(BaseModel):
    item_type: Optional[str] = Field(default=None, description="e.g. ring, necklace, bracelet, watch, earring")
    material_or_color: Optional[str] = Field(default=None, description="e.g. silver-colored, gold-colored, leather")
    location: Optional[str] = Field(default=None, description="Anatomical location e.g. right ring finger, left wrist, neck")
    description: Optional[str] = Field(default=None, description="Description e.g. silver-colored band ring on right ring finger")
    status: str = Field(default="OBSERVED", description="OBSERVED, INFERRED, or UNKNOWN")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: Optional[str] = None


class TattooObservation(BaseModel):
    description: Optional[str] = Field(default=None, description="Visual description of tattoo e.g. bird-like tattoo in flight")
    location: Optional[str] = Field(default=None, description="Anatomical placement e.g. right shoulder, left forearm, upper chest")
    design_motifs: List[str] = Field(default_factory=list, description="Key motif keywords e.g. ['bird', 'wings', 'flying']")
    colors: List[str] = Field(default_factory=list, description="Colors observed in tattoo e.g. ['black ink', 'blue']")
    status: str = Field(default="OBSERVED", description="OBSERVED, INFERRED, or UNKNOWN")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: Optional[str] = None


class ScarObservation(BaseModel):
    description: Optional[str] = Field(default=None, description="Visual mark description e.g. linear surgical scar approx 3 cm")
    location: Optional[str] = Field(default=None, description="Anatomical placement e.g. left forearm, right cheek, abdomen")
    mark_type: Optional[str] = Field(default=None, description="scar, birthmark, mole, lesion, injury mark")
    status: str = Field(default="OBSERVED", description="OBSERVED, INFERRED, or UNKNOWN")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    notes: Optional[str] = None


class PhysicalCharacteristicObservation(BaseModel):
    attribute: Optional[str] = Field(default=None, description="e.g. hair_color, hair_length, facial_hair, apparent_age_group, build")
    value: Optional[str] = Field(default=None, description="Observed visual value or UNKNOWN")
    status: str = Field(default="OBSERVED", description="OBSERVED, INFERRED, or UNKNOWN")
    confidence: float = Field(default=0.80, ge=0.0, le=1.0)
    notes: Optional[str] = None


class ImageQuality(BaseModel):
    status: str = Field(default="GOOD", description="GOOD, FAIR, POOR, or DEGRADED")
    occlusion: bool = Field(default=False, description="True if significant visual occlusion exists")
    occlusion_details: Optional[str] = Field(default=None, description="Description of occlusion if present")
    lighting: Optional[str] = Field(default="ADEQUATE", description="ADEQUATE, LOW_LIGHT, OVEREXPOSED, HARSH_SHADOWS")
    resolution_assessment: Optional[str] = Field(default="SUFFICIENT", description="SUFFICIENT, LOW_RESOLUTION, BLURRY")


class ObservationsContainer(BaseModel):
    clothing: List[ClothingObservation] = Field(default_factory=list)
    jewellery: List[JewelleryObservation] = Field(default_factory=list)
    tattoos: List[TattooObservation] = Field(default_factory=list)
    scars_or_marks: List[ScarObservation] = Field(default_factory=list)
    physical_characteristics: List[PhysicalCharacteristicObservation] = Field(default_factory=list)
    visible_text: List[str] = Field(default_factory=list, description="Any text or numbers visibly legible in image")
    other_observations: List[str] = Field(default_factory=list, description="Other notable forensic visual observations")


class ImageExtraction(BaseModel):
    record_type: str = Field(default="AM", description="AM or PM")
    image_type: str = Field(default="OTHER", description="PORTRAIT, FULL_BODY, CLOTHING, TATTOO, SCAR, JEWELLERY, BODY_OVERVIEW, INJURY, DENTAL, OTHER")
    observations: ObservationsContainer = Field(default_factory=ObservationsContainer)
    image_quality: ImageQuality = Field(default_factory=ImageQuality)
    summary: Optional[str] = Field(default=None, description="Concise objective visual summary of observable evidence")

    model_config = ConfigDict(extra="ignore")
