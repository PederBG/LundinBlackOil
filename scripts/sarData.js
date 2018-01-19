/**
 * Created by PederGB on 10.07.2017.
 */
 var listFiles = [];

var xhr = new XMLHttpRequest();
xhr.onreadystatechange = function() {
    if (xhr.readyState == XMLHttpRequest.DONE) {
        var result = xhr.response;
        result = result.split("\n");

	var names = [];
	var links = [];
        for (var i = (result.length - 2); i > -1; i--){ // result.lenght-1 is undefined
            names.push(result[i].split(" ")[0]);
            links.push(result[i].split(" ")[1]);
        }


        console.log(names);
        console.log(links);

        for (i in names) {
            console.log(names[i]);
            listFiles.push(names[i]);
            var res = document.createElement("div");
            res.setAttribute("class", "responsive");
            document.getElementById("images").appendChild(res);

            var gal = document.createElement("div");
            gal.setAttribute("class", "gallery");
            res.appendChild(gal);

            var tar = document.createElement("a");
            tar.setAttribute("onclick", "togglePopup(this)");
            gal.appendChild(tar);

            var img = document.createElement("img");
            img.setAttribute("src", names[i].split(".jpg")[0] + "_t.jpg");
            img.setAttribute("height", "400");
            img.setAttribute("width", "600");
            tar.appendChild(img);

            var desc = document.createElement("div");
            desc.setAttribute("class", "desc");
            //desc.setAttribute("href", "sentinel_images_clean/sentinel-image(C)_15-09-2017_15-35.png");
            var temp = names[i].split('.jpg')[0].split('sentinel_images/')[1];
            if (temp.indexOf(':') == -1) {
                tempName = temp.split('-').slice(0,4).join('-') + ':' + temp.split('-')[4]; //Used to display time bether
            }
            else {
                tempName = temp;
            }
            testName = "<div onclick='downloadClearImage(this)' style='cursor:pointer;'>" + tempName + "</div>";

            if (i < (result.length - 2) - 35){ // Bad solution, but works..
                desc.innerHTML = testName;
            }
            else{
                desc.innerHTML = tempName
            }
            gal.appendChild(desc)

            var popup = document.createElement("div");
            popup.setAttribute("class", "popup");
            res.appendChild(popup);
            
            var clearImage = "sentinel_images_clear/" + names[i].split('/')[1].split('.jpg')[0] + "_c.jpg"
            console.log(clearImage)

            popup.innerHTML = "<a href=" + names[i] + " class='popup_first'><p>View Image</p></a><a id=" + temp + " onclick='showMapWithKmlURL(this.id)' style='cursor: pointer'>" + "<p>View in Map</p>" + "</a>" + "<a href="+links[i]+">" + "<p>Download Raw Data</p>" + "</a><a href=" + clearImage + " style='cursor: pointer'><p>View Clear Image</p></a>";
        }
    }
};
xhr.open('GET', '/peder/product_download_links.txt', true);
xhr.send(null);


function showMapWithKmlURL(image){
    localStorage.setItem("kmlURL", "http://lundinblackoil.com/peder/kmlfiles/" + image + ".kml");
    console.log(image)
    window.open('map.html', "_self");
}

function togglePopup(e){
    if (e.parentNode.parentNode.children[1].style.display == 'block'){
        e.parentNode.parentNode.children[1].style.display = 'none';
        e.parentNode.style.opacity = '1';
    }
    else {
        var selects = document.getElementsByClassName('popup');
        for(var i = 0; i < selects.length; i++){
            selects[i].style.display = 'none';
            selects[i].parentNode.firstChild.style.opacity= '1';
        }
        e.parentNode.parentNode.children[1].style.display = 'block';
        e.parentNode.style.opacity = '0.8';
    }
}
/*
function downloadClearImage(image){
    clearImage = 'sentinel_images_clean/' + image.innerHTML.split('image')[0] + 'image(c)' + image.innerHTML.split('image')[1] + '.jpg';
    compPath = clearImage.split(':')[0] + '-' + clearImage.split(':')[1]
    window.location = compPath; //TODO fix this!
}
*/

document.addEventListener("click", function(e){
    console.log(e.target.tagName);
    if (e.target.tagName == 'HTML' || e.target.tagName == 'A' || e.target.tagName == 'UL'){
        var selects = document.getElementsByClassName('popup');
        for(var i = 0; i < selects.length; i++){
            selects[i].style.display = 'none';
            selects[i].parentNode.firstChild.style.opacity= '1';
        }
    }
});



