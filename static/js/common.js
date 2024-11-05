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
