const chatHtml = `
<div id="chat-floating-widget" style="position: fixed; bottom: 20px; right: 20px; width: 350px; height: 450px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; flex-direction: column; font-family: Arial, sans-serif; z-index: 9999;">
    <div style="background-color: #007bff; color: white; padding: 12px; border-top-left-radius: 9px; border-top-right-radius: 9px; font-weight: bold; display: flex; justify-content: space-between; align-items: center;">
        <span>RAG BookBot</span>
        <span style="font-size: 12px; opacity: 0.8;">UPB Lab</span>
    </div>
    
    <div id="chat-box" style="flex: 1; overflow-y: auto; padding: 15px; background-color: #f8f9fa;">
        <div style="margin-bottom: 10px; background-color: #e9ecef; padding: 8px 12px; border-radius: 8px; max-width: 85%; font-size: 14px;">
            Hey there! I am your book assistant. How can I help you today?
        </div>
    </div>
    
    <div id="chat-starters-buttons" style="padding: 8px; background-color: #ffffff; border-top: 1px solid #f1f1f1; display: flex; flex-wrap: wrap; gap: 4px;">
        </div>
    
    <div style="padding: 10px; border-top: 1px solid #e0e0e0; display: flex; background-color: #ffffff; border-bottom-left-radius: 9px; border-bottom-right-radius: 9px;">
        <input type="text" id="user-input" style="flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px; outline: none; font-size: 14px;" placeholder="Ask me something...">
        <button id="send-btn" style="margin-left: 5px; background-color: #007bff; color: white; border: none; padding: 8px 14px; border-radius: 4px; cursor: pointer; font-weight: bold;">Send</button>
    </div>
</div>
`;

document.addEventListener("DOMContentLoaded", () => {
    // inyectamos el widget HTML directamente en el cuerpo d la pagina actual
    const chatContainer = document.createElement('div');
    chatContainer.innerHTML = chatHtml;
    document.body.appendChild(chatContainer.firstChild);
    
    // leemos DOM HTML
    const pageType = document.body.getAttribute("data-page-type") || "generic";
    const bookTitle = document.body.getAttribute("data-book-title") || "";
    const bookGenre = document.body.getAttribute("data-book-genre") || "";
    const bookAuthor = document.body.getAttribute("data-book-author") || "";

    // ejecutamos la carga de sugerencias
    initConversationStarters(pageType, bookTitle, bookGenre, bookAuthor);

    // mapear evento de envío del input manual
    document.getElementById("send-btn").addEventListener("click", () => {
        const input = document.getElementById("user-input");
        if (input && input.value.trim() !== "") {
            sendQueryToAssistant(input.value);
            input.value = "";
        }
    });
});

function initConversationStarters(pageType, title, genre, author) {
    const startersContainer = document.getElementById('chat-starters-buttons');
    if (!startersContainer) return;
    
    startersContainer.innerHTML = '';
    let suggestions = [];

    // sugerencias basadas en el estado de la navegación del cliente
    if (pageType === "list") {
        suggestions = [
            "What is a book that I am most likely to enjoy from this list?",
            "What genres are available?",
            "Show me beginner level books."
        ];
    } else if (pageType === "detail" && title) {
        suggestions = [
            `Who wrote the book ${title}?`,
            `What is the genre of ${title}?`,
            `Is ${title} suitable for my reading level?`
        ];
    } else {
        // fallback
        suggestions = [
            "Reccomend me a science fiction book",
            "What are my favourite topics?",
            "Help me search a book by his author."
        ];
    }

    // renderizar los tres bloques de interaccion controlada
    suggestions.slice(0, 3).forEach(text => {
        const button = document.createElement('button');
        button.innerText = text;
        button.style.backgroundColor = "#e2e8f0";
        button.style.border = "none";
        button.style.borderRadius = "15px";
        button.style.padding = "6px 12px";
        button.style.fontSize = "12px";
        button.style.cursor = "pointer";
        button.style.color = "#334155";
        button.style.transition = "background-color 0.2s";
        
        button.onmouseover = () => button.style.backgroundColor = "#cbd5e1";
        button.onmouseout = () => button.style.backgroundColor = "#e2e8f0";
        button.onclick = () => sendQueryToAssistant(text);
        
        startersContainer.appendChild(button);
    });
}
/* not implemented yet
function sendQueryToAssistant(text) {
    const inputField = document.getElementById('user-input');
    if (inputField) {
        inputField.value = text;
        //aqui mandaremos la consulta al rag
    }
        
}
    */