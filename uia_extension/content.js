console.log('Content JS injected!');

document.addEventListener('mouseup', function() {
    let selectedText = window.getSelection().toString().trim();
    if (selectedText.length > 0) {
      chrome.runtime.sendMessage({
        action: 'saveText',
        text: selectedText
      }, function(response) {
        console.log(response);
      });
    }
  });

// 在页面 DOM 加载完成后执行操作
document.addEventListener('readystatechange', function(event) {
    if(false && "complete"===document.readyState){
        const div = document.createElement('div');
        div.setAttribute('style','position: absolute;left: 10%;top: 10%;BACKGROUND-COLOR:#CCCC66;Z-INDEX:9999;')
        div.textContent = 'This content is injected by Chrome extension.';
        document.body.appendChild(div);
        //
        const ipt = document.getElementById('kw');
        ipt.value="test";
        //
        const btn = document.getElementById('su');
        btn.click();
    }
  });
