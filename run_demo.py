"""
SmartPark Vision AI - Sovereign Demo Runner.
Launches the interactive Web Command Center on port 8080.
Run this script to demonstrate the complete AI parking and surveillance system.
"""

import sys
import os
import webbrowser
import uvicorn

# Ensure repository root is in python path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)


def main():
    port = int(os.environ.get("PORT", "8088"))
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print("=" * 80)
    print("  Smart Park - Centre de Contrôle et Démo Interactive")
    print("  Conforme Loi 18-07 & Loi 25-11 (République Algérienne Démocratique et Populaire)")
    print("=" * 80)
    print(f"[*] Serveur Souverain Démarré sur : {url}")
    print("[*] Stockage Local & RAM FAISS   : Actifs (<0.8ms recherche)")
    print("[*] Moteur Plaques Algériennes  : Actif (6 chiffres + provisoire 00 + 58 wilayas)")
    print("[*] Anti-Spoofing MiniFASNet    : Actif (Double optique RGB + 850nm NIR)")
    print("[*] Contrôleur Relais Barrière  : Mode Simulation Actif (500ms impulsion)")
    print("-" * 80)
    print("  Scénarios pré-intégrés pour la démonstration client :")
    print("    [1] Accès VIP Instantané (Amine Hadj - 104822 119 16)")
    print("    [2] Véhicule Neuf Plaque Provisoire (08412 00 16)")
    print("    [3] Alerte Sécurité Véhicule Volé (00551 218 16)")
    print("    [4] Fraude Photo / Écran Détectée (Anti-Spoofing)")
    print("    [5] Discordance Chauffeur / Voiture (Validation Garde)")
    print("    [6] Règlement Sortie Chargily Pay V2 (CIB / Edahabia)")
    print("    [Espace] Déclenchement Manuel Barrière")
    print("=" * 80)
    print(f"[>] Ouvrez votre navigateur sur : {url}")
    print("=" * 80)

    # Launch Uvicorn
    uvicorn.run("src.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
