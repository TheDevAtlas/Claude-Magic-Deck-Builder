# Claude Magic Deck Builder
A desktop application that helps Magic: The Gathering players build and optimize their decks with AI assistance from Anthropic's Claude.

## Overview
Magic Deck Builder is a powerful tool that combines a visual card management interface with AI recommendations. The application allows you to:

* Search and add cards from the Scryfall database
* Scan physical cards using your webcam
* Get deck-building advice from Claude AI
* Export your deck to text format

## Requirements
* Python3.12 or higher
* Python-venv with Linux
* Linux or Powershell

## Powershell Installation:
Installation:

Run
`pip install -r requirments.txt`

## Linux Installation:
Installation:

Run
`bash setup.sh`

## Usage for Linux and Powershell:
### Open an interactive GUI
* Add claude api key into deck_builder.py
`client = anthropic.Anthropic(api_key='')`
* Run `python deck_builder.py`

### Adding Cards
* Type a card name in the search bar and press Enter or click "Add Card"
* Use the camera icon to scan physical cards
* Use + and - buttons to adjust quantities

### Getting AI Assistance

Type questions or requests in the chat box

Examples:

* "What cards would strengthen my green creatures strategy?"
* "Suggest a good mana base for this deck"
* "What's a good counter to aggro decks I could add?"

### Exporting Your Deck
Click "Export Deck" to save your deck list as a text file

## License
This project is provided as-is for educational purposes.

## Acknowledgments
* Scryfall for their comprehensive MTG card database API
* Anthropic for the Claude AI assistant API