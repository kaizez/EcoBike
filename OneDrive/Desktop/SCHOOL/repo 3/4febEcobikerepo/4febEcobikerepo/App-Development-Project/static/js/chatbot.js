document.addEventListener("DOMContentLoaded", function () {
    const chatBubble = document.getElementById("chat-bubble");
    const chatBox = document.getElementById("chat-box");
    const chatClose = document.getElementById("chat-close");
    const chatInput = document.getElementById("chat-input");
    const chatSend = document.getElementById("chat-send");
    const chatMessages = document.getElementById("chat-messages");
    const chatStop = document.createElement("button");

    let controller = null;

    // Configure Stop AI button
    chatStop.textContent = "Stop AI";
    chatStop.style.display = "none";
    chatStop.style.margin = "10px 0";
    chatStop.style.padding = "5px 10px";
    chatStop.style.backgroundColor = "#FF4C4C";
    chatStop.style.color = "white";
    chatStop.style.border = "none";
    chatStop.style.borderRadius = "5px";
    chatStop.style.cursor = "pointer";
    chatStop.style.fontSize = "14px";
    chatStop.addEventListener("click", stopAI);
    chatBox.appendChild(chatStop);

    chatBubble.addEventListener("click", () => {
        chatBox.style.display = chatBox.style.display === "block" ? "none" : "block";
    });

    chatClose.addEventListener("click", () => {
        chatBox.style.display = "none";
    });

    chatSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") sendMessage();
    });

    async function sendMessage() {
        let userMessage = chatInput.value.trim();
        if (!userMessage) return;

        addMessage("You: " + userMessage, "user");
        chatInput.value = "";
        chatInput.disabled = true;
        chatSend.disabled = true;
        chatStop.style.display = "inline-block";

        let aiMessageContainer = addMessage("AI: ", "ai");

        controller = new AbortController();

        try {
            const response = await fetch("/chatbot", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMessage }),
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const reader = response.body.getReader();
            let decoder = new TextDecoder();
            let aiResponse = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                let chunk = decoder.decode(value, { stream: true });

                aiResponse += chunk;
                aiMessageContainer.textContent = "AI: " + aiResponse;
            }

        } catch (error) {
            if (error.name === "AbortError") {
                aiMessageContainer.textContent = "AI response stopped.";
            } else {
                aiMessageContainer.textContent = "Error: Could not reach AI.";
                console.error("Fetch error:", error);
            }
        } finally {
            chatInput.disabled = false;
            chatSend.disabled = false;
            chatStop.style.display = "none";
            controller = null;
        }
    }

    function stopAI() {
        if (controller) {
            controller.abort();
            controller = null;
        }
    }

    function addMessage(text, sender) {
        let messageElement = document.createElement("div");
        messageElement.textContent = text;
        messageElement.classList.add(sender);
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageElement;
    }
});
