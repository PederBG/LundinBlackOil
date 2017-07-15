/**
 * Created by PederGB on 10.07.2017.
 */
 var listFiles = [];
 
var xhr = new XMLHttpRequest();
xhr.onreadystatechange = function() {
    if (xhr.readyState == XMLHttpRequest.DONE) {
        var names = xhr.response;
        names = names.split("<ul>")[1];
        names = names.split("</ul>")[0];
        names = names.split("</li>").slice(1);

        var files = [];
        for (var i = 0; i < names.length -1; i++){
            files.push(names[i].split('"')[1]);
        }


        console.log(files);


        for (i in files) {
            listFiles.push(files[i]);
            var res = document.createElement("div");
            res.setAttribute("class", "responsive");
            document.getElementById("images").appendChild(res);

            var gal = document.createElement("div");
            gal.setAttribute("class", "gallery");
            res.appendChild(gal);

            var tar = document.createElement("a");
            tar.setAttribute("target", "_blank");
            tar.setAttribute("href", "sentinel_images/"+ files[i]);
            gal.appendChild(tar);

            var img = document.createElement("img");
            img.setAttribute("src", "sentinel_images/" + files[i]);
            img.setAttribute("height", "200");
            img.setAttribute("width", "300");
            tar.appendChild(img);

            var desc = document.createElement("div");
            desc.setAttribute("class", "desc");
            var temp = files[i].split('.png')[0];
            desc.innerHTML = temp.split('./')[1];
            gal.appendChild(desc)
        }
    }
};
xhr.open('GET', '/peder/sentinel_images', true);
xhr.send(null);