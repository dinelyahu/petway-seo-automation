let currentProduct = null


function loadProduct(product){

    currentProduct = product

    document.getElementById("productTitle").innerText = product.name

    document.getElementById("name").value = product.name || ""

    document.getElementById("price").value = product.price || ""

    document.getElementById("price_discount").value = product.price_discount || ""

    setBrand(product)

    renderVariations(product)

}



function setBrand(product){

    const select = document.getElementById("brand")

    if(!select) return

    if(product.brand_value)
        select.value = product.brand_value

}



function renderVariations(product){

    const container = document.getElementById("variationsContainer")

    container.innerHTML = ""

    if(!product.variations || product.variations.length === 0){

        container.innerHTML = "<div>אין תכונות</div>"
        return

    }

    product.variations.forEach(v => {

        const row = document.createElement("div")
        row.className = "variation"

        row.innerHTML = `

            <label>כותרת</label>
            <input class="varTitle" value="${v.title}">

            <label>מחיר</label>
            <input class="varPrice" value="${v.price}">

            <label>מחיר הנחה</label>
            <input class="varDiscount" value="${v.price_discount || ""}">

            <label>מלאי</label>
            <input class="varStock" value="${v.stock || ""}">

        `

        container.appendChild(row)

    })

}



function collectVariations(){

    const rows = document.querySelectorAll(".variation")

    const variations = []

    rows.forEach(r => {

        const title = r.querySelector(".varTitle").value
        const price = r.querySelector(".varPrice").value
        const discount = r.querySelector(".varDiscount").value
        const stock = r.querySelector(".varStock").value

        variations.push({

            title:title,
            price:price,
            price_discount:discount,
            stock:stock

        })

    })

    return variations

}



function saveProduct(){

    const data = {

        id:currentProduct.id,

        name:document.getElementById("name").value,

        price:document.getElementById("price").value,

        price_discount:document.getElementById("price_discount").value,

        brand_id:document.getElementById("brand").value,

        variations:collectVariations()

    }


    fetch("/api/update_product",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify(data)

    })
    .then(r=>r.json())
    .then(res=>{

        alert("המוצר עודכן")

    })

}