from typing import Dict, Any, List
import json

university_names = [
    "Abertay University",
    "Aberystwyth University",
    "Anglia Ruskin University",
    "Arts University Bournemouth",
    "Aston University",
    "Bangor University",
    "Bath Spa University",
    "BIMM Institute London",
    "Birkbeck, University of London",
    "Birmingham City University",
    "Bishop Grosseteste University",
    "Bournemouth University",
    "BPP University",
    "Brunel University London",
    "Buckinghamshire New University",
    "Canterbury Christ Church University",
    "Cardiff Metropolitan University",
    "Cardiff University",
    "City, University of London",
    "Coventry University",
    "Cranfield University",
    "De Montfort University",
    "Durham University",
    "Edge Hill University",
    "Edinburgh Napier University",
    "European School of Economics",
    "Falmouth University",
    "Glasgow Caledonian University",
    "Goldsmiths, University of London",
    "Guildhall School of Music and Drama",
    "Harper Adams University",
    "Hartpury University and Hartpury College",
    "Heriot-Watt University",
    "Imperial College London",
    "Keele University",
    "King's College London",
    "Kingston University",
    "Lancaster University",
    "Leeds Arts University",
    "Leeds Beckett University",
    "Leeds Conservatoire",
    "Leeds Trinity University",
    "Liverpool Hope University",
    "Liverpool Institute for Performing Arts",
    "Liverpool John Moores University",
    "Liverpool School of Tropical Medicine",
    "London Business School",
    "London Metropolitan University",
    "London School of Hygiene and Tropical Medicine, University of London",
    "London South Bank University",
    "Loughborough University",
    "Manchester Metropolitan University",
    "Middlesex University",
    "Newcastle University",
    "Newman University, Birmingham",
    "Northern School of Contemporary Dance",
    "Northumbria University",
    "Norwich University of the Arts",
    "Nottingham Trent University",
    "Oxford Brookes University",
    "Plymouth College of Art",
    "Plymouth Marjon University",
    "Queen Margaret University",
    "Queen Mary University of London",
    "Queen's University Belfast",
    "Ravensbourne University London",
    "Regent's University London",
    "Richmond, The American International University in London",
    "Robert Gordon University",
    "Rose Bruford College",
    "Royal Academy of Music, University of London",
    "Royal Agricultural University",
    "Royal College of Art",
    "Royal College of Music",
    "Royal Conservatoire of Scotland",
    "Royal Holloway, University of London",
    "Royal Northern College of Music",
    "Royal Veterinary College University of London",
    "School of Advanced Study, University of London",
    "Scotland's Rural College",
    "Sheffield Hallam University",
    "SOAS, University of London",
    "Solent University",
    "St George's, University of London",
    "St Mary's University, Twickenham",
    "Staffordshire University",
    "Swansea University",
    "Teesside University",
    "The Courtauld Institute of Art, University of London",
    "The Glasgow School of Art",
    "The London Institute of Banking and Finance",
    "The London School of Economics and Political Science",
    "The Royal Central School of Speech and Drama",
    "The University of Buckingham",
    "The University of Edinburgh",
    "The University of Hull",
    "The University of Law",
    "The University of Manchester",
    "The University of Northampton",
    "The University of Nottingham",
    "The University of Sheffield",
    "The University of Warwick",
    "The University of Winchester",
    "The University of York",
    "Trinity Laban Conservatoire of Music and Dance",
    "Ulster University",
    "University College Birmingham",
    "University College London",
    "University for the Creative Arts",
    "University of Aberdeen",
    "University of Bath",
    "University of Bedfordshire",
    "University of Birmingham",
    "University of Bolton",
    "University of Bradford",
    "University of Brighton",
    "University of Bristol",
    "University of Central Lancashire",
    "University of Chester",
    "University of Chichester",
    "University of Cumbria",
    "University of Derby",
    "University of Dundee",
    "University of East Anglia",
    "University of East London",
    "University of Essex",
    "University of Exeter",
    "University of Glasgow",
    "University of Gloucestershire",
    "University of Greenwich",
    "University of Hertfordshire",
    "University of Huddersfield",
    "University of Kent",
    "University of Leeds",
    "University of Leicester",
    "University of Lincoln",
    "University of Liverpool",
    "University of London",
    "University of Plymouth",
    "University of Portsmouth",
    "University of Reading",
    "University of Roehampton",
    "University of Salford",
    "University of South Wales",
    "University of Southampton",
    "University of St Andrews",
    "University of Stirling",
    "University of Strathclyde",
    "University of Suffolk",
    "University of Sunderland",
    "University of Surrey",
    "University of Sussex",
    "University of the Arts London",
    "University of the Highlands and Islands",
    "University of the West of England",
    "University of the West of Scotland",
    "University of Wales",
    "University of Wales Trinity Saint David",
    "University of West London",
    "University of Westminster",
    "University of Wolverhampton",
    "University of Worcester",
    "Wrexham Glyndwr University",
    "Writtle University College",
    "York St John University",
    "University of Oxford",
    "University of Cambridge"
]


university_names_simplified = [x.lower().replace(" ", "") for x in university_names]


class Arguments:

    def __init__(self, event: Dict[str, Any]):
        self._required_args = None
        self.error = None
        self._arguments = self._get_arguments(event)

    def available(self):
        return self._arguments is not None

    def _get_arguments(self, event: Dict[str, Any]):
        cleaned_body = event["body"].replace("\n", "")
        try:
            return json.loads(cleaned_body)
        except json.decoder.JSONDecodeError as e:
            self.error = "ERROR"
            return None

    def contains(self, expected_parameters: List[str]):
        return all(x in self._arguments for x in expected_parameters)

    def contains_requirements(self):
        return all(x in self._arguments for x in self._required_args)

    def keys(self):
        return self._arguments.keys()

    def require(self, x: List[str]):
        self._required_args = x

    def requirements(self):
        return self._required_args

    def __getitem__(self, item):
        return self._arguments[item]

    def get(self, item):
        return self[item]