from typing import Annotated

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
)


def desc(d):
    return Field(description=d)


class RBBase(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    def model_dump_yaml(self, stream=None, **kwargs):
        args = {
            "default_flow_style": kwargs.get("default_flow_style", False),
            "allow_unicode": kwargs.get("allow_unicode", True),
            "width": kwargs.get("width", 1000),
        }
        return yaml.dump(self.model_dump(), stream, **args)


# class SiteUrl(RBBase):
#     site: str
#     url: HttpUrl
type SiteUrl = Annotated[dict[str, HttpUrl], desc("A website and url")]


class ContactInfo(RBBase):
    """
    Contact Information
    """

    email: EmailStr = desc("Email Address")
    phone: str = desc("Phone Number")
    location: str = Field(
        description="Location or street address",
        alias=AliasChoices("location", "address"),
    )
    # TODO: make urls a list
    urls: dict[str, HttpUrl] = desc("URLs for websites (e.g. linkedin: https://...")


class PersonalInformation(RBBase):
    """
    Personal details about the applicant
    """

    name: str = desc("Name of the applicant")
    contact: ContactInfo | None = Field(
        default=None, description="Contact info for the applicant"
    )
    tagline: str = desc(
        "Your field of expertise, the title of the job being "
        "applied to, or a very brief description of the applicant"
    )
    summary: str = desc(
        "Paragraph(s) describing the applicant and their strengths/skills/etc."
    )


type SkillCategory = Annotated[dict[str, list[str]], desc("Skills in a cat")]


class EducationEntry(RBBase):
    """
    School attended or currently attending
    """

    school: str = desc(
        "Name of school or the organazation giving degree or certification"
    )
    degree: str = desc("Location of school or organazation")
    location: str | None = Field(
        default=None, description="Type and name of degree or certification"
    )
    year: int | None = Field(
        default=None,
        description="Year in which degree or certification was received (or expected to be received)",
    )


type MonthYear = tuple[int, int] | int | str


type NestedJobDetail = Annotated[
    str | list[NestedJobDetail] | dict[str, NestedJobDetail],
    desc("""
    Can be given 3 ways:
      - A simple string (e.g. a sentence or paragraph description)
      - A list of items
      - - Lists are rendered as bullet lists
      - - Items in the list can be arbitrary combinations of strings, mappings, or more lists
      - - Nested lists become nested levels of bullet points
      - A key/value mapping
      - - The key is a header or category for the description (e.g. "Responsibilities")
      - - The value can either be the description as a string, another mapping, or a list of items
      - - Lists are handled the same as they are outside of mappings
    """),
]


class JobPosition(RBBase):
    """
    A job position held (or currently holding)
    """

    title: str = desc("Job title")
    sub_title: str | None = Field(
        description="Job title",
        default=None,
        alias=AliasChoices("sub-title", "sub_title"),
    )
    start_date: MonthYear | None = Field(default=None, description="Start date of job")
    end_date: MonthYear | None = Field(
        default=None, description="End date of job (optional if currently holding)"
    )
    details: NestedJobDetail = Field(
        description="Details, description, or explanation of the job, e.g. responsibilities, accomplishments, etc.",
        default=None
    )


class ExperienceEmployer(RBBase):
    """
    An employer and list of jobs held
    """

    company: str = desc("Name of employer")
    location: str = desc("Location of employer")
    start_date: MonthYear = Field(description="Start date with employer")
    end_date: MonthYear | None = Field(
        default=None,
        description="End date with employer (optional if current employer)",
    )
    positions: list[JobPosition] = desc("List of positions held with employer")


class Resume(RBBase):
    """
    Resume object definition
    """

    personal: PersonalInformation = desc("Personal information")
    skills: list[SkillCategory] = desc("Skills/keywords")
    experience: list[ExperienceEmployer] = desc("Work Experience")
    education: list[EducationEntry] = desc("Education")
