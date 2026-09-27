# Petway — AI-Powered E-Commerce Automation

A Python automation platform built for a real e-commerce workflow to reduce repetitive product-management and SEO work across a large online catalog.

The system combines **Selenium browser automation**, **AI-assisted content generation**, reusable product-management modules and a lightweight **Flask admin interface**.

## What It Automates

The project includes workflows for:

- Creating and updating products
- Generating and refining product content with AI
- SEO-oriented product enrichment
- Category assignment
- Product information and pricing updates
- Product variations and deals
- FAQ generation
- Product image workflows
- Facebook-related utilities
- Bulk catalog administration

The goal was to turn repetitive manual store operations into reusable automated workflows, saving substantial manual work when operating across thousands of products.

## Architecture

```text
petway-seo-automation/
├── bot/
│   ├── products/          # Product creation and enrichment
│   ├── update/            # Existing-product update workflows
│   ├── auth.py            # Browser setup and store authentication
│   ├── categories.py      # Category logic
│   ├── chat.py            # AI-assisted content workflow
│   ├── facebook.py        # Facebook-related automation
│   └── update_product.py
├── data/
│   └── categories_mapping.xlsx
├── scripts/
│   └── cli_product_creator.py
├── static/                # Front-end JavaScript
├── templates/             # Flask interface templates
├── app.py                 # Web application entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file from the example:

```bash
copy .env.example .env
```

Add your own credentials to `.env`, then start the web interface:

```bash
python app.py
```

The original system was built around a live store, so browser selectors and some workflows are environment-specific.

## Technologies

`Python` `Selenium` `Flask` `Anthropic API` `LLMs` `Automation` `E-Commerce` `SEO`

## What This Project Demonstrates

- Automation of a real business workflow
- Modular Python application design
- Browser automation with Selenium
- AI-assisted content generation
- Large-catalog product management
- Integration with external services
- Building a simple web interface around automation workflows

## Public Portfolio Version

This repository is a sanitized portfolio version of the original project. Real credentials, `.env` files, Git history, IDE metadata, caches, backups and unrelated/duplicate project folders have been removed.
