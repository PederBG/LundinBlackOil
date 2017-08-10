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
        for (var i = 0; i < result.length -1; i++){
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
            tar.setAttribute("target", "_blank");
            tar.setAttribute("href", names[i]);
            gal.appendChild(tar);

            var img = document.createElement("img");
            img.setAttribute("src", names[i].split(".png")[0] + "(R).png");
            img.setAttribute("height", "200");
            img.setAttribute("width", "300");
            tar.appendChild(img);

            var desc = document.createElement("div");
            desc.setAttribute("class", "desc");
            var temp = names[i].split('.png')[0].split('sentinel_images/')[1];
            console.log(temp)
            if (temp.indexOf(':') == -1) {
                tempName = temp.split('-').slice(0,4).join('-') + ':' + temp.split('-')[4]; //Used to display time bether
            }
            else {
                tempName = temp;
            }
            if (links[i] != "NO_LINK"){
                desc.innerHTML = tempName + "<a id=" + temp + " onclick='showMapWithKmlURL(this)' style='cursor: pointer'>" + "<p>View in Map</p>" + "</a>" + "<a href="+links[i]+">" + "<p>Download Raw Data</p>" + "</a>";
            }
            else {
                desc.innerHTML = temp;
            }
            gal.appendChild(desc)
        }
    }
};
xhr.open('GET', '/peder/product_download_links.txt', true);
xhr.send(null);


function showMapWithKmlURL(e){
    localStorage.setItem("kmlURL", "http://lundinblackoil.com/peder/kmlfiles/" + e.id + ".kml");
    window.open('map.html', "_self");
}