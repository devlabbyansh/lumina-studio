# Lumina Studio

**AI-Powered Image Editing Studio built with Flask, OpenCV and NLP.**

Lumina Studio is a web-based image editing application that combines computer vision techniques with natural language processing to provide an interactive image editing experience.

## Features

- Background Removal using GrabCut
- Chroma Key Background Removal
- Image Filters and Color Grading
- CLAHE Enhancement
- Cartoon, Sketch and Emboss Effects
- Image Crop, Rotate and Flip
- Image Eraser
- SVG Vectorization
- Image Histogram Visualization
- Undo and Editing History
- NLP-Based Editing Assistant
- Export Images in PNG, JPEG, WEBP and SVG

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend Development |
| Flask | Web Framework |
| OpenCV | Computer Vision |
| NumPy | Image Processing |
| HTML5 | Frontend Structure |
| CSS3 | Styling |
| JavaScript | Frontend Logic |
| NLP | Natural Language Commands |

## Project Structure

```text
lumina-studio/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── image_ops.py
│   └── nlp.py
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
├── templates/
│   ├── index.html
│   ├── about.html
│   └── docs.html
├── .gitignore
└── requirements.txt
```

## Installation & Setup

**1. Clone the repository**

```bash
git clone https://github.com/devlabbyansh/lumina-studio.git
cd lumina-studio
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Run the application**

```bash
python backend/app.py
```

**4. Open in browser**

```text
http://127.0.0.1:3000
```

## Future Improvements

- Advanced AI-powered editing commands
- More computer vision effects
- Improved image processing performance
- Cloud deployment and accessibility

## Author

**Ansh (devlabbyansh)**

GitHub: https://github.com/devlabbyansh

---

*Built with Python, Flask, OpenCV and JavaScript.*
