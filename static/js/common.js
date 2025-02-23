// function setup_csrf() {
//     function getCookie(name) {
//         var cookieValue = null;
//         if (document.cookie && document.cookie !== '') {
//             var cookies = document.cookie.split(';');
//             for (var i = 0; i < cookies.length; i++) {
//                 var cookie = jQuery.trim(cookies[i]);
//                 if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                     cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                     break;
//                 }
//             }
//         }
//         return cookieValue;

//     }
//     var csrftoken = getCookie('csrftoken');
//     function csrfSafeMethod(method) {
//         return (/^(GET|HEAD    // Function to get the CSRF token from the cookies
//     function getCookie(name) {
//         let cookieValue = null;
//         if (document.cookie && document.cookie !== '') {
//             const cookies = document.cookie.split(';');
//             for (let i = 0; i < cookies.length; i++) {
//                 const cookie = cookies[i].trim();
//                 // Does this cookie string begin with the name we want?
//                 if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                     cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                     break;
//                 }
//             }
//         }
//         return cookieValue;
//     }|OPTIONS|TRACE)$/.test(method));
//     }
//     $.ajaxSetup({
//         beforeSend: function(xhr, settings) {
//             if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
//                 xhr.setRequestHeader("X-CSRFToken", csrftoken);
//             }
//         }
//     });
// }

function splitIfContains(inputString, delimiter) {
    if (inputString.includes(delimiter)) {
        return inputString.split(delimiter);
    } else {
        return [inputString]; // Return the original string in an array if delimiter is not found
    }
}

function setup_csrf() {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
        return (/^GET|HEAD|OPTIONS|TRACE$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    })
}

function getDictionary(type, key) {
    setup_csrf()
    let result = "";
    $.ajax({
        url: '/api/global/dictionary/' + type + '/' + key + '/',
        async: false, // Set to false to make the request synchronous
        success: function(response) {
            result = response;
        },
        error: function(xhr, status, error) {
            console.error('Error fetching dictionary:', xhr, status, error);
        }
    });
    return result;
}

function createActionLink(id, pattern, url) {
    let result = ""
    if(pattern.endsWith('-filter')){
        result = url.replace(pattern, '/'+id+'-filter')
    }else if (pattern.endsWith('-filter/')){
        result = url.replace(pattern, '/'+id+'-filter/')
    }else if (pattern.endsWith('/') && pattern.startsWith('/')){
        result = url.replace(pattern, '/'+id+'/')
    }
    return result
}

function createFileDownloadLink(file, file_download_url) {
    let result = ""
    if(file instanceof Array){
        file.forEach(record => {
            let url = createActionLink(record['id'], '/0-filter', file_download_url)
            result = result + '<a href="'+url+ '" download>'+record['name']+'</a>&nbsp;'
        })
    } else{
        let url = createActionLink(file['id'], '/0-filter', file_download_url)
        result = result + '<a href="'+url+ '" download>'+file['name']+'</a>'
    }
    return result
}

function getData(link) {
    let result = "";
    $.ajax({
        url: link,
        async: false, // Set to false to make the request synchronous
        success: function(response) {
            result = response;
        },
        error: function(xhr, status, error) {
            console.error('Error fetching dictionary:', xhr, status, error);
            createMessageBox('System Error', 'error');
        }
    });
    if (result['message'] != undefined) {
        createMessageBox(result['message'], 'warning')
    }
    return result;
}

function createMessageBox(message, type, setTimeout = false, timeout = 3000) {
    // type: 'error', 'warning', '' ( ''=success)
    // Get the parent of the existing element
    const parentElement = document.getElementById("content-start");
    // Create a new div element
    const messageBox = document.createElement('li');
    messageBox.className = `${type}`;
    messageBox.textContent = message;

    // Check if the message box already exists and remove it if it does
    var existingMessageBox = parentElement.querySelector('.messagelist');

    if (existingMessageBox == null) {
        existingMessageBox = document.createElement('ul');
        existingMessageBox.className = 'messagelist';
        existingMessageBox.appendChild(messageBox);
        // Get the element you want to insert BEFORE
        const existingElement = document.getElementById("content"); // Or any other selector
        // Insert the new element before the existing element
        parentElement.insertBefore(existingMessageBox, existingElement);
    } else {
        existingMessageBox.appendChild(messageBox);
    }
    if (setTimeout == true) {
        setTimeout(() => {
            messageBox.remove();
        }, timeout);
    }
    return messageBox;
}

function createInputError(parentElement, message) {
    // Create a new div element
    const messageBox = document.createElement('li');
    // messageBox.className = 'w3-red';
    messageBox.textContent = message;

    // Check if the message box already exists and remove it if it does
    var existingMessageBox = parentElement.querySelector('.errorlist');

    if (existingMessageBox == null) {
        existingMessageBox = document.createElement('ul');
        existingMessageBox.className = 'errorlist';
        existingMessageBox.appendChild(messageBox);
        // inputElement.insertAdjacentElement('afterend', existingMessageBox);
        parentElement.appendChild(existingMessageBox)
    } else {
        existingMessageBox.appendChild(messageBox);
    }
}