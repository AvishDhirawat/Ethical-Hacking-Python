var zoneList = [
    "UK", "NY", "WA", "SG", "DE", "TX", "HK", "LA", "GA", "SYD", "BU", "JP", "FR", "KC", "MI", "MN", "AMS", "SIL", "BR", "ES", "IL", "NO", "RU", "IT", "JH", "IN", "CZ", "TR", "PL", "CA", "TH", "LT", "PER", "MEL", "AUC", "BRB", "ASB", "KR", "ADL", "AT", "FI", "ISR", "VA", "AE", "DEN", "SE", "CH", "ND", "NG", "CL", "BG", "PT", "DK", "BE", "IE", "PHX", "CEN", "GR", "EG", "SK", "KE", "MX", "KZ", "AR", "CR", "UA", "CO", "PE", "EC", "RJ", "ID", "VN", "PH", "MY", "PA", "FO", "LJ", "LU", "MS", "MD", "CY", "BA", "GEO", "LV", "HU", "AZ", "HOU", "RS", "PK", "IS", "TW", "IQ", "OG", "RI", "PR", "HI", "GT", "BS", "CT", "BO", "AM", "FU", "BHR", "PP", "NP", "MG", "BD", "HR", "CLT", "MSP", "GU", "IQ2", "SSA", "CWB", "LAP", "MI2", 
];

var currentZoneIndex = 0;

// Shuffle an array
function shuffle(array) {
    let currentIndex = array.length, randomIndex;

    while (currentIndex != 0) {
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;
        [array[currentIndex], array[randomIndex]] = [
            array[randomIndex], array[currentIndex]];
    }

    return array;
}

function runMetricsTest() {
    fetch('https://metrics-bunny.net/test/register')
      .then(function(response) {
        return response.json();
      })
      .then(function(data) {
        var uniqueId = data.uniqueId;
        var url = 'https://' + uniqueId + '.metrics-bunny.net/test/hello';
        return fetch(url);
      })
      .then(function(response) {
        return response.text(); // Use .json() here if you expect JSON
      })
      .then(function(result) {
        console.log('Final response:', result);
      })
      .catch(function(error) {
        console.error('Error:', error);
      });
  }

function scheduleNextTest() {
    currentZoneIndex++;
    if (currentZoneIndex < zoneList.length) {
        setTimeout(runNextTest, 500);
    }
}

function runNextTest() {
    var startTime = new Date().valueOf();

    var currentZoneCode = zoneList[currentZoneIndex].toLowerCase();
    var startTime = new Date().valueOf();
    var fetchUrl = 'https://edgezone-' + currentZoneCode + '.bunnyinfra.net/500b.jpg?s=' + startTime;
    fetch(fetchUrl)
        .then(data => {
            startTime = new Date().valueOf();
            fetch(fetchUrl)
                .then(data => {
                    var endTime = new Date().valueOf();
                    var diff = endTime - startTime;
                    fetch('https://rum-metrics.bunny.net/trackperformance?zone=' + currentZoneCode + '&latency=' + diff);
                    scheduleNextTest();
                }).catch((error) => { scheduleNextTest(); });
        }).catch((error) => { scheduleNextTest(); });
}

shuffle(zoneList);
runNextTest();
runMetricsTest();