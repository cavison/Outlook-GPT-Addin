// Outlook Add-in for Email Rewriting using ChatGPT
(function () {
    Office.onReady(function (info) {
        if (info.host === Office.HostType.Outlook) {
            Office.context.mailbox.item.body.getAsync("text", function (result) {
                if (result.status === Office.AsyncResultStatus.Failed) {
                    console.error("Failed to get email body");
                }
            });
        }
    });
})();

function rewriteEmail() {
    Office.context.mailbox.item.body.getAsync("text", function (result) {
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            let emailBody = result.value;
            
            // Call ChatGPT API
            fetch("YOUR_CHATGPT_API_ENDPOINT", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: emailBody })
            })
            .then(response => response.json())
            .then(data => {
                let rewrittenText = data.rewritten_text;
                
                // Replace email body with rewritten version
                Office.context.mailbox.item.body.setAsync(rewrittenText, { coercionType: "text" }, function (asyncResult) {
                    if (asyncResult.status === Office.AsyncResultStatus.Failed) {
                        console.error("Failed to update email body");
                    }
                });
            })
            .catch(error => console.error("Error calling ChatGPT API:", error));
        }
    });
}

Office.actions.associate("rewriteEmail", rewriteEmail);
