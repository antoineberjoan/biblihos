"""
Scraper francescpi.com — extraction des données SCPI.

Usage :
    python -m scrapers.scpi.francescpi corum-origin
    python -m scrapers.scpi.francescpi corum-origin --output data/scpi/corum/origin.yaml
    python -m scrapers.scpi.francescpi --list

Le scraper tente d'abord le JSON-LD embarqué dans la page, puis des
sélecteurs CSS en fallback. Il affiche ce qu'il trouve et ce qu'il rate,
pour faciliter le debug.
"""

import argparse
import json
import re
import sys
import pathlib
import yaml
from dataclasses import dataclass, field, asdict


# ── Types de sortie ───────────────────────────────────────────────────

@dataclass
class ScpiScrapee:
    """Données brutes extraites de francescpi.com — avant normalisation YAML."""
    slug: str
    url: str

    # Identité
    nom: str = "—"
    societeGestion: str = "—"
    type: str = "SCPI"
    isin: str = "—"
    dateCreation: str = "—"
    capitalisation: str = "—"
    strategie: str = "—"
    risque: str = "—"
    sfdr: str = "—"
    isr: bool = False
    labelIsr: str = "—"
    versement: str = "—"
    delaiJouissance: str = "—"

    # Frais
    fraisSouscription: object = "—"
    fraisGestion: object = "—"
    fraisAcquisition: object = "—"
    fraisRevente: object = "—"
    fraisTravaux: object = "—"

    # Prix
    prixSouscription: object = "—"
    prixRetrait: object = "—"
    valeurReconstitution: object = "—"
    minimumSouscription: object = "—"

    # Performance (td courant)
    td_courant: object = "—"
    td_annee_courante: str = "—"

    # Patrimoine
    tof: object = "—"
    nombreActifs: object = "—"
    walb: object = "—"
    endettement: object = "—"

    # Historique brut : {annee: {prixSouscription, td}}
    historique: dict = field(default_factory=dict)

    # Démembrement brut : {duree: nue_propriete}
    demembrement: dict = field(default_factory=dict)

    # Debug : champs trouvés vs manqués
    trouves: list = field(default_factory=list)
    manques: list = field(default_factory=list)


# ── Parseurs utilitaires ──────────────────────────────────────────────

def parse_pct(text: str) -> object:
    """'12,00 %' → 0.12 | '—' si non parsable."""
    if not text:
        return "—"
    text = text.strip().replace(",", ".").replace("\xa0", "").replace(" ", "")
    match = re.search(r"([\d.]+)\s*%", text)
    if match:
        return round(float(match.group(1)) / 100, 6)
    return "—"


def parse_montant(text: str) -> object:
    """'1 135 €' → 1135.0 | '—' si non parsable."""
    if not text:
        return "—"
    text = text.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    # Supprimer les séparateurs de milliers (point ou espace)
    text = re.sub(r"[^\d.]", "", text)
    try:
        return float(text)
    except ValueError:
        return "—"


def parse_annee(text: str) -> str:
    """Extrait une année sur 4 chiffres."""
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else "—"


# ── Extraction JSON-LD ────────────────────────────────────────────────

def extraire_json_ld(page) -> dict:
    """Cherche et parse tous les blocs JSON-LD de la page."""
    blocs = {}
    for tag in page.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.text)
            schema_type = data.get("@type", "inconnu")
            blocs[schema_type] = data
        except (json.JSONDecodeError, AttributeError):
            continue
    return blocs


def extraire_depuis_json_ld(scrape: ScpiScrapee, blocs: dict) -> None:
    """Remplit les champs depuis les blocs JSON-LD."""
    # Type Product ou RealEstateListing
    product = blocs.get("Product") or blocs.get("RealEstateListing") or {}

    if prix := product.get("offers", {}).get("price") or product.get("price"):
        scrape.prixSouscription = float(prix)
        scrape.trouves.append("prixSouscription (JSON-LD)")

    if nom := product.get("name"):
        scrape.nom = nom
        scrape.trouves.append("nom (JSON-LD)")

    if description := product.get("description"):
        # Chercher le TD dans la description
        match = re.search(r"(\d+[,.]?\d*)\s*%", description)
        if match:
            scrape.td_courant = round(float(match.group(1).replace(",", ".")) / 100, 6)
            scrape.trouves.append("td_courant (JSON-LD description)")

    # Organisation = société de gestion
    if org := product.get("brand", {}).get("name") or blocs.get("Organization", {}).get("name"):
        scrape.societeGestion = org
        scrape.trouves.append("societeGestion (JSON-LD)")


# ── Extraction CSS — sélecteurs à confirmer après test ───────────────

def extraire_depuis_css(scrape: ScpiScrapee, page) -> None:
    """
    Fallback CSS. Les sélecteurs sont des candidats basés sur l'analyse
    de la structure de francescpi.com — à ajuster après observation réelle.
    """

    def essayer(champ: str, selecteurs: list[str], parseur=None):
        """Essaie chaque sélecteur, prend le premier qui retourne du texte."""
        for selecteur in selecteurs:
            try:
                element = page.css(selecteur).first
                if element and element.text.strip():
                    valeur = parseur(element.text) if parseur else element.text.strip()
                    setattr(scrape, champ, valeur)
                    scrape.trouves.append(f"{champ} (CSS: {selecteur})")
                    return
            except Exception:
                continue
        if getattr(scrape, champ) == "—":
            scrape.manques.append(champ)

    # Nom
    if scrape.nom == "—":
        essayer("nom", ["h1", ".scpi-name", ".page-title h1", "[itemprop='name']"])

    # Société de gestion
    if scrape.societeGestion == "—":
        essayer("societeGestion", [
            ".societe-gestion", ".management-company",
            "[itemprop='brand']", ".scpi-manager",
        ])

    # Prix de souscription
    if scrape.prixSouscription == "—":
        essayer("prixSouscription", [
            ".prix-souscription", ".price-part", ".prix-part",
            "[data-field='prix_souscription']", ".rendement-icon-3",
        ], parse_montant)

    # TD courant
    if scrape.td_courant == "—":
        essayer("td_courant", [
            ".taux-distribution", ".td-value", ".rendement-annuel",
            "[data-field='td']", ".rendement-icon-9",
        ], parse_pct)

    # Frais de souscription
    essayer("fraisSouscription", [
        ".frais-souscription", "[data-field='frais_souscription']",
        "td:contains('Frais de souscription') + td",
        ".commission-souscription",
    ], parse_pct)

    # Frais de gestion
    essayer("fraisGestion", [
        ".frais-gestion", "[data-field='frais_gestion']",
        "td:contains('Frais de gestion') + td",
    ], parse_pct)

    # TOF
    essayer("tof", [
        ".tof", ".taux-occupation", "[data-field='tof']",
        "td:contains('Taux d') + td",
    ], parse_pct)

    # Délai de jouissance
    essayer("delaiJouissance", [
        ".delai-jouissance", "[data-field='delai_jouissance']",
        "td:contains('Délai de jouissance') + td",
    ])

    # Stratégie / type de SCPI
    essayer("strategie", [
        ".strategie", ".type-scpi", "[data-field='strategie']",
        ".scpi-type",
    ])

    # SRI / Risque
    essayer("risque", [
        ".sri", ".risque", "[data-field='sri']",
        ".indicateur-risque .value",
    ])


# ── Extraction données JS (historique, démembrement) ─────────────────

def extraire_depuis_scripts(scrape: ScpiScrapee, page) -> None:
    """
    Cherche les données de charts Chart.js et les tables de démembrement
    dans les blocs <script> inline.
    """
    for script_tag in page.css("script:not([src])"):
        script_text = script_tag.text or ""

        # ── Historique TD (Chart.js pattern) ──────────────────────────
        # Pattern typique : labels: ["2018","2019",...] data: [5.9, 6.2, ...]
        if "labels" in script_text and ("td" in script_text.lower() or "distribution" in script_text.lower()):
            annees = re.findall(r'"(20\d{2})"', script_text)
            valeurs = re.findall(r'data:\s*\[([^\]]+)\]', script_text)
            if annees and valeurs:
                valeurs_liste = [v.strip() for v in valeurs[0].split(",")]
                if len(annees) == len(valeurs_liste):
                    for annee, valeur in zip(annees, valeurs_liste):
                        try:
                            scrape.historique[annee] = {
                                "td": round(float(valeur) / 100, 6),
                                "prixSouscription": "—",
                            }
                        except ValueError:
                            pass
                    if scrape.historique:
                        scrape.trouves.append(f"historique td ({len(scrape.historique)} années)")

        # ── Historique prix de part ────────────────────────────────────
        if "prixSouscription" in script_text or "prix_souscription" in script_text or "prix de part" in script_text.lower():
            annees = re.findall(r'"(20\d{2})"', script_text)
            valeurs = re.findall(r'data:\s*\[([^\]]+)\]', script_text)
            if annees and valeurs:
                valeurs_liste = [v.strip() for v in valeurs[0].split(",")]
                if len(annees) == len(valeurs_liste):
                    for annee, valeur in zip(annees, valeurs_liste):
                        try:
                            if annee not in scrape.historique:
                                scrape.historique[annee] = {"prixSouscription": "—", "td": "—"}
                            scrape.historique[annee]["prixSouscription"] = float(valeur)
                        except ValueError:
                            pass

        # ── Démembrement ──────────────────────────────────────────────
        # Pattern : {"5": 79, "10": 67, "15": 59} ou tableau [durée, np, us]
        if "demembrement" in script_text.lower() or "nue-propriete" in script_text.lower() or "nue_propriete" in script_text.lower():
            match = re.search(r'\{[^}]*"5"[^}]*\}', script_text)
            if match:
                try:
                    raw = json.loads(match.group(0))
                    for duree, valeur in raw.items():
                        try:
                            scrape.demembrement[str(int(duree))] = round(float(valeur) / 100, 4)
                        except (ValueError, TypeError):
                            pass
                    if scrape.demembrement:
                        scrape.trouves.append(f"démembrement ({len(scrape.demembrement)} durées)")
                except json.JSONDecodeError:
                    pass


# ── Scraping principal ────────────────────────────────────────────────

BASE_URL = "https://francescpi.com/scpi-de-rendement"


def scraper_scpi(slug: str) -> ScpiScrapee:
    """Scrape une SCPI depuis francescpi.com."""
    try:
        from scrapling.fetchers import PlayWrightFetcher
    except ImportError:
        print("Erreur : scrapling non installé. Lancer : pip install 'scrapling[all]' && scrapling install", file=sys.stderr)
        sys.exit(1)

    url = f"{BASE_URL}/{slug}"
    scrape = ScpiScrapee(slug=slug, url=url)

    print(f"Scraping : {url}", file=sys.stderr)
    fetcher = PlayWrightFetcher(auto_match=True)

    try:
        page = fetcher.fetch(url, timeout=30)
    except Exception as error:
        print(f"Erreur de connexion : {error}", file=sys.stderr)
        sys.exit(1)

    if page.status != 200:
        print(f"HTTP {page.status} — page introuvable ou bloquée", file=sys.stderr)
        sys.exit(1)

    # Extraction dans l'ordre de fiabilité
    blocs_json_ld = extraire_json_ld(page)
    extraire_depuis_json_ld(scrape, blocs_json_ld)
    extraire_depuis_css(scrape, page)
    extraire_depuis_scripts(scrape, page)

    # Champs non trouvés
    champs_attendus = [
        "nom", "societeGestion", "prixSouscription", "prixRetrait",
        "td_courant", "fraisSouscription", "fraisGestion", "tof",
        "delaiJouissance", "strategie", "risque",
    ]
    for champ in champs_attendus:
        if getattr(scrape, champ, "—") == "—" and champ not in scrape.manques:
            scrape.manques.append(champ)

    return scrape


# ── Conversion vers format YAML biblihos ─────────────────────────────

def vers_yaml_biblihos(scrape: ScpiScrapee) -> dict:
    """Convertit ScpiScrapee vers la structure YAML biblihos."""
    # Historique : on s'assure que td_courant est dans historique si on a l'année
    if scrape.td_courant != "—" and scrape.td_annee_courante != "—":
        annee = scrape.td_annee_courante
        if annee not in scrape.historique:
            scrape.historique[annee] = {"prixSouscription": "—", "td": "—"}
        if scrape.historique[annee].get("td") == "—":
            scrape.historique[annee]["td"] = scrape.td_courant

    return {
        # Identité
        "nom": scrape.nom,
        "societeGestion": scrape.societeGestion,
        "type": scrape.type,
        "isin": scrape.isin,
        "dateCreation": scrape.dateCreation,
        "creation": "—",
        "capitalisation": scrape.capitalisation,
        "capitalVariable": True,
        "strategie": scrape.strategie,
        "risque": scrape.risque,
        "sfdr": scrape.sfdr,
        "isr": scrape.isr,
        "labelIsr": scrape.labelIsr,
        "versement": scrape.versement,
        "versementProgramme": False,
        "delaiJouissance": scrape.delaiJouissance,
        "url": scrape.url,

        # Frais
        "fraisSouscription": scrape.fraisSouscription,
        "fraisGestion": scrape.fraisGestion,
        "fraisAcquisition": scrape.fraisAcquisition,
        "fraisRevente": scrape.fraisRevente,
        "fraisTravaux": scrape.fraisTravaux,

        # Prix
        "prixSouscription": scrape.prixSouscription,
        "prixRetrait": scrape.prixRetrait,
        "valeurReconstitution": scrape.valeurReconstitution,
        "minimumSouscription": scrape.minimumSouscription,
        "pga": "—",

        # Performance
        "td": {scrape.td_annee_courante: scrape.td_courant} if scrape.td_courant != "—" else {},

        # Patrimoine
        "tof": scrape.tof,
        "top": "—",
        "nombreActifs": scrape.nombreActifs,
        "nombreLocataires": "—",
        "walb": scrape.walb,
        "endettement": scrape.endettement,
        "associes": "—",

        # Répartition — à remplir manuellement ou via scraper dédié
        "repartitionGeographique": {},
        "repartitionSectorielle": {},

        # Liquidité
        "liquidite": "Illiquide",
        "souscriptions": "—",
        "retraits": "—",
        "ran": "—",

        # Démembrement
        "demembrement": scrape.demembrement or {
            "3": "—", "4": "—", "5": "—", "6": "—", "7": "—",
            "8": "—", "9": "—", "10": "—", "15": "—", "20": "—",
        },

        # Historique
        "historique": scrape.historique,

        # Documents
        "documents": {
            "dic": {"url": "—", "date": "—"},
            "rapportAnnuel": {"url": "—", "date": "—"},
            "bulletinTrimestriel": {"url": "—", "date": "—"},
            "noteInformations": {"url": "—", "date": "—"},
        },
    }


# ── Récupération de la liste de toutes les SCPI ──────────────────────

def lister_scpis() -> list[dict]:
    """Récupère la liste des slugs SCPI depuis la page de listing."""
    try:
        from scrapling.fetchers import PlayWrightFetcher
    except ImportError:
        print("Erreur : scrapling non installé. Lancer : pip install 'scrapling[all]' && scrapling install", file=sys.stderr)
        sys.exit(1)

    fetcher = PlayWrightFetcher(auto_match=True)
    page = fetcher.fetch("https://francescpi.com/scpi-de-rendement/", timeout=30)

    scpis = []
    for lien in page.css("a[href*='/scpi-de-rendement/']"):
        href = lien.attrib.get("href", "")
        # Extraire le slug (exclure la page de listing elle-même)
        match = re.search(r"/scpi-de-rendement/([^/?#]+)$", href)
        if match:
            slug = match.group(1)
            nom = lien.text.strip() or slug
            if slug and slug not in [scpi["slug"] for scpi in scpis]:
                scpis.append({"slug": slug, "nom": nom})

    return scpis


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape une SCPI depuis francescpi.com"
    )
    parser.add_argument(
        "slug",
        nargs="?",
        help="Slug de la SCPI (ex: corum-origin, iroko-zen)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Fichier de sortie YAML (défaut: stdout)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister tous les slugs disponibles sur francescpi.com",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Afficher les champs trouvés et manquants",
    )
    args = parser.parse_args()

    if args.list:
        scpis = lister_scpis()
        print(f"\n{len(scpis)} SCPI trouvées :\n")
        for scpi in scpis:
            print(f"  {scpi['slug']:40s} {scpi['nom']}")
        return

    if not args.slug:
        parser.print_help()
        sys.exit(1)

    scrape = scraper_scpi(args.slug)

    if args.debug or not args.output:
        print("\n── Champs extraits ──────────────────────────────────", file=sys.stderr)
        for champ in scrape.trouves:
            print(f"  ✓ {champ}", file=sys.stderr)
        if scrape.manques:
            print("\n── Champs manquants ─────────────────────────────────", file=sys.stderr)
            for champ in scrape.manques:
                print(f"  ✗ {champ}", file=sys.stderr)
        print("", file=sys.stderr)

    data = vers_yaml_biblihos(scrape)

    yaml_output = yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    if args.output:
        output_path = pathlib.Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml_output, encoding="utf-8")
        print(f"Sauvegardé : {output_path}", file=sys.stderr)
    else:
        print(yaml_output)


if __name__ == "__main__":
    main()
