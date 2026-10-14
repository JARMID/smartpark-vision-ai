# Guide de Démonstration Client - SmartPark Vision AI
**Plateforme Souveraine de Vidéosurpveillance, ALPR et Contrôle d'Accès Biométrique**  
*Conforme Loi 18-07 et Loi 25-11 (République Algérienne Démocratique et Populaire)*

---

## 1. Résumé Exécutif pour la Direction

SmartPark Vision AI est une solution d'accès et de vidéosurveillance intelligente conçue spécifiquement pour le marché algérien. Contrairement aux solutions étrangères qui transmettent les flux vidéo et les données biométriques vers des serveurs cloud situés à l'étranger, SmartPark Vision AI fonctionne selon un principe de souveraineté absolue :
1. **Zéro transfert transfrontalier :** Conforme à l'Article 44 de la Loi 18-07 et aux dispositions de la Loi 25-11 du 24 juillet 2025. Toutes les données biométriques restent hébergées sur le site ou dans un centre de données national.
2. **Décision barrière en moins de 250 millisecondes :** La comparaison vectorielle s'exécute en mémoire vive locale (RAM FAISS) en 0.74 milliseconde. Une coupure de connexion Internet ne bloque jamais l'entrée ou la sortie des véhicules.
3. **Moteur ALPR algérien natif :** Reconnaissance optique calibrée pour les plaques minéralogiques algériennes, incluant les séries récentes à six chiffres (wilayas 16, 31, 09) et les cartes grises provisoires au code temporaire 00.
4. **Paiement sans attente aux barrières :** Intégration de Chargily Pay V2 pour les cartes Edahabia et CIB en paiement préalable sur smartphone ou borne de hall, évitant tout embouteillage au niveau de la voie de sortie.
5. **Jumeau numérique 3D et CAD 2D :** Visualisation spatiale WebGL temps réel de l'ensemble du parking avec contrôle orbital, levée mécanique des barrières, cônes de vision des caméras et plan architectural métrique.

---

## 2. Comment Lancer la Démonstration (En Moins de 10 Secondes)

Le dossier du projet a été configuré pour fonctionner sans aucune friction technique, quel que soit l'ordinateur utilisé par votre interlocuteur.

### Option A : Lancement en un clic sous Windows (Recommandé)
Double-cliquez simplement sur le fichier :
```text
start_demo.bat
```
Ce script vérifie la présence de Python, installe les modules requis si nécessaire, démarre le serveur local et ouvre automatiquement votre navigateur sur `http://127.0.0.1:8080`.

### Option B : Mode Autonome sans Aucune Dépendance (Zéro Installation)
Si la personne ne dispose pas des droits administrateur ou n'a pas installé Python :
- Double-cliquez sur `start_browser_only.bat`, ou
- Ouvrez directement le fichier `static/index.html` dans Google Chrome, Microsoft Edge ou Mozilla Firefox.

L'interface bascule alors en mode simulation autonome locale. Tous les graphismes, animations de caméras, alarmes sonores et déclenchements de scénarios fonctionnent directement dans le navigateur.

### Option C : Lancement Manuel sous Linux ou macOS
Ouvrez un terminal dans le dossier et exécutez :
```bash
chmod +x start_demo.sh
./start_demo.sh
```
Ou directement avec Python :
```bash
python3 run_demo.py
```

### Option D : Conteneurisation Docker
Si vous disposez de Docker Desktop :
```bash
docker compose up -d
```

---

## 3. Déroulé des 6 Scénarios de Démonstration

Une barre de raccourcis située en haut de l'écran permet de lancer immédiatement six cas d'usage réels en appuyant sur les touches `1` à `6` ou en cliquant sur les boutons colorés.

### Scénario 1 : Accès VIP Instantané (Touche [1])
* **Contexte :** Véhicule d'un abonné de direction ou VIP enregistré dans la base de données.
* **Plaque :** `104822 119 16` (Alger, berline de tourisme de l'année 2019).
* **Déroulement :**
  1. CAM-01 détecte la plaque d'immatriculation et identifie la wilaya d'Alger (16).
  2. CAM-02 capture le visage du conducteur à travers le pare-brise. L'algorithme ArcFace calcule une distance cosinus de 0.42 (inférieure au seuil de validation de 0.52).
  3. Le module MiniFASNet confirme un indice de vivacité humaine de 98%.
  4. La barrière s'ouvre en 180 millisecondes et un carillon sonore valide l'accès.

### Scénario 2 : Véhicule Neuf avec Plaque Provisoire 00 (Touche [2])
* **Contexte :** Véhicule neuf récemment dédouané ou sorti de concession, en circulation avec une carte grise provisoire.
* **Plaque :** `08412 00 16` (Le code central 00 indique une immatriculation temporaire légale).
* **Déroulement :**
  1. Le moteur ALPR reconnaît la syntaxe spéciale `\d{1,6} 00 \d{2}` sans la rejeter en erreur.
  2. Le système constate l'absence d'abonnement VIP et bascule sur le parcours visiteur.
  3. Un ticket QR horodaté est imprimé à la borne et la barrière s'ouvre pour autoriser le stationnement.

### Scénario 3 : Véhicule Volé ou Recherché (Touche [3])
* **Contexte :** Véhicule inscrit sur la liste de surveillance de la sécurité publique.
* **Plaque :** `00551 218 16` (Signalement vol en cours).
* **Déroulement :**
  1. La plaque est détectée sur CAM-01 et vérifiée instantanément contre la liste d'alerte en RAM.
  2. La barrière reste strictement verrouillée.
  3. Un avertisseur sonore retentit et une notification rouge d'alerte de sécurité est consignée dans le journal d'audit.

### Scénario 4 : Tentative de Fraude par Photo ou Écran (Touche [4])
* **Contexte :** Un individu présente une photo ou une vidéo d'un abonné VIP sur une tablette face à la caméra pour tenter d'usurper son identité.
* **Déroulement :**
  1. CAM-02 observe le signal optique combinant lumière visible et infrarouge proche 850nm.
  2. L'algorithme MiniFASNet détecte l'absence de micro-textures dermiques et les reflets caractéristiques d'un écran (score de vivacité de 0.22).
  3. L'accès est refusé avec le motif "Attaque par présentation détectée", protégeant les parkings sensibles contre les usurpations.

### Scénario 5 : Discordance Véhicule et Conducteur (Touche [5])
* **Contexte :** Le véhicule correspond bien à un abonné régulier, mais la personne au volant n'est pas le titulaire du badge.
* **Plaque :** `04122 118 16` (Karim Benali).
* **Déroulement :**
  1. La plaque est validée.
  2. Le visage du conducteur présente une distance de 0.62 (supérieure au seuil de 0.55).
  3. La barrière ne s'ouvre pas automatiquement. Le système bascule en validation manuelle par l'agent de garde, évitant le vol de véhicules d'abonnés par des tiers.

### Scénario 6 : Sortie Fluide Réglée par Chargily Pay V2 (Touche [6])
* **Contexte :** Un visiteur quitte le parking après avoir réglé son stationnement via carte Edahabia ou CIB.
* **Déroulement :**
  1. Le client a scanné son ticket QR sur son téléphone avant de rejoindre son véhicule et a réglé 200 DZD via la passerelle Chargily Pay V2.
  2. Le système lui a accordé une fenêtre de grâce de 15 minutes.
  3. Dès son arrivée sur CAM-03, la plaque `08192 120 09` est lue. Le système confirme le statut payé et lève la lisse mécanique immédiatement.

---

## 4. Conformité Réglementaire ANPDP (Loi 18-07 et Loi 25-11)

Cliquez sur le bouton **Loi 25-11** dans la barre supérieure de l'interface pour afficher le dossier juridique complet :
* **Stockage souverain :** L'Article 44 de la Loi 18-07 interdit formellement le transfert de données à caractère personnel vers des pays étrangers sans autorisation préalable. SmartPark Vision AI garantit un traitement local sur site ou hébergé chez un opérateur de télécommunication public algérien.
* **AIPD / DPIA obligatoire :** L'article 21-1 introduit par la Loi 25-11 impose une analyse d'impact préalable pour tout traitement biométrique. Le système utilise des vecteurs numériques 512-D normalisés qui ne permettent aucune reconstruction photographique inverse.
* **Registre de traitement :** Le système intègre nativement les quatre catégories légales avec des durées de rétention calibrées (30 jours glissants pour les plaques et photos d'accès, archivage fiscal d'un an pour les horodatages comptables).
* **Gestion des incidents de sécurité :** Module de notification d'incident sous 5 jours calendrier auprès de l'ANPDP conformément aux nouvelles exigences de la Loi 25-11.

---

## 5. Raccourcis Clavier pour la Démonstration

| Raccourci | Action Immédiate |
| :--- | :--- |
| `1` | Lancer Scénario 1 (Entrée VIP Amine Hadj) |
| `2` | Lancer Scénario 2 (Plaque Provisoire 00) |
| `3` | Lancer Scénario 3 (Véhicule Volé) |
| `4` | Lancer Scénario 4 (Fraude Photo / Écran) |
| `5` | Lancer Scénario 5 (Chauffeur Inconnu) |
| `6` | Lancer Scénario 6 (Sortie Réglée Chargily Pay) |
| `Espace` | Déclenchement manuel de la barrière Voie 1 |
| `Échap` | Fermer les fenêtres modales ouvertes |

---

## 6. Budget Matériel Estimatif (Marché d'Alger)

Pour un déploiement commercial pilote sur un site comprenant une voie d'entrée et une voie de sortie :

| Composant | Référence Recommandée | Coût Estimé (DZD) |
| :--- | :--- | :--- |
| Serveur Edge AI | Intel Core i5-13400, 32 Go RAM, SSD NVMe 1 To, GPU NVIDIA RTX 3060 12 Go ou RTX 4060 | ~185,000 DZD |
| Onduleur Online Double Conversion | Onduleur 2kVA / 1800W avec carte de communication USB / SNMP | ~120,000 DZD |
| Caméras ALPR Voies 1 et 2 | 2x Caméras IP 4MP Global Shutter avec filtre polarisant CPL | ~90,000 DZD |
| Caméras Bornes Visage | 2x Caméras double optique RGB + Infrarouge proche 850nm | ~75,000 DZD |
| Caméras Surveillance Stalles | 4x Dômes IP 4MP grand angle | ~70,000 DZD |
| Équipements Réseau & Contrôle | Switch PoE+ manageable 16 ports et contrôleur relais Modbus TCP | ~40,000 DZD |
| **Total Matériel Estimé** | **Solution complète clé en main pour 8 caméras** | **~580,000 DZD** |

---

## 7. Vérification Technique et Tests Automatisés

Le code source inclut une suite de tests unitaires et d'intégration validant chaque couche algorithmique. Pour exécuter la suite de tests :
```bash
python -m unittest discover tests
```
Résultat garanti : 33 tests exécutés avec succès couvrant le parseur de plaques, l'index vectoriel en RAM, le tampon SQLite hors-ligne, le contrôleur Modbus et l'API FastAPI.
