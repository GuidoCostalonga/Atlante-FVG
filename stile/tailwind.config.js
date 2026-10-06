// Configurazione di Tailwind CSS 3.4 per l'Atlante: colori e caratteri della pagina.
// Lo stile si compila con scripts/compila_stile.js e finisce dentro index.html.
module.exports = {
  content: ['./index.html'],
  theme: { extend: {
    colors: {
      primario: { 50: '#F0F6FB', 100: '#E1EDF7', 200: '#B6D4EE', 500: '#1B6FB5', 600: '#155E9E', 700: '#0E4273', 800: '#0B3359', 900: '#07213A' },
      accento: { 50: '#FFFDF5', 100: '#FEF8E3', 200: '#FCEBB9', 300: '#F7D678', 400: '#F2B94A', 500: '#D8973C', 600: '#B67524', 700: '#8A5313' },
      enfasi: { 50: '#FDF2F2', 500: '#C1292E', 600: '#A41D22', 700: '#7E1317' },
      pietra: { 50: '#FAF9F6', 100: '#F4F1EA', 200: '#E6E0D4', 300: '#D4CBBF', 700: '#52565E', 800: '#32353B', 900: '#202226' },
      verde: { 50: '#EEF7F1', 600: '#2F7D4F', 700: '#24613D' }
    },
    fontFamily: {
      patriarcale: ['"Source Serif 4"', 'Georgia', 'serif'],
      sans: ['"Plus Jakarta Sans"', 'system-ui', 'Segoe UI', 'sans-serif']
    }
  } }
};
