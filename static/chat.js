(() => {
 const form=document.getElementById("chat-form"), input=document.getElementById("chat-input");
 const list=document.getElementById("chat-messages"), feedback=document.getElementById("feedback");
 if(!form) return;
 let conversationId=null;
 function addMessage(text,who){
   const row=document.createElement("div"); row.className="message "+(who==="customer"?"user-msg":"bot-msg");
   if(who==="bot"){const av=document.createElement("div");av.className="msg-avatar";av.textContent="S";row.appendChild(av);}
   const content=document.createElement("div");content.className="msg-content";
   const p=document.createElement("p");p.textContent=text;content.appendChild(p);
   const time=document.createElement("time");time.textContent="Just now";content.appendChild(time);
   row.appendChild(content);list.appendChild(row);list.scrollTop=list.scrollHeight;
 }
 form.addEventListener("submit",async e=>{
   e.preventDefault();const message=input.value.trim();if(!message)return;
   addMessage(message,"customer");input.value="";input.disabled=true;
   try{
     const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message,conversation_id:conversationId})});
     const data=await res.json();if(!res.ok)throw new Error(data.error||"Something went wrong.");
     conversationId=data.conversation_id;addMessage(data.reply,"bot");feedback.hidden=false;
   }catch(err){addMessage(err.message||"Unable to connect. Please try again.","bot");}
   finally{input.disabled=false;input.focus();}
 });
 document.querySelectorAll("[data-rating]").forEach(btn=>btn.addEventListener("click",async()=>{
   if(!conversationId)return;
   const status=document.getElementById("feedback-status");
   try{const res=await fetch("/api/feedback",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({conversation_id:conversationId,rating:btn.dataset.rating})});const data=await res.json();status.textContent=res.ok?data.message:(data.error||"Could not save feedback.");}
   catch(e){status.textContent="Could not save feedback.";}
 }));
})();
