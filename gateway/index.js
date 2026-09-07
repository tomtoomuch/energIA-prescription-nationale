const express = require("express");
const axios = require("axios");
const app = express();
const path = require("path");
const port = process.env.GATEWAY_PORT || 3000;
const PYTHON_API_URL = (
    process.env.PYTHON_SERVICE_URL ||
    "http://ms-python:8000"
).replace(/\/+$/, "");

const PYTHON_API_URL_2 = (
    process.env.PYTHON_SERVICE_URL_2 ||
    "http://ms-python-2:8002"
).replace(/\/+$/, "");
const PYTHON_MCP_URL = (
    process.env.PYTHON_MCP_URL ||
    "http://mcp-server:8003"
).replace(/\/+$/, "");
const SECURITY_TOKEN = process.env.SECURITY_TOKEN;

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));



function pythonHeaders() {
    return { "x-api-key": SECURITY_TOKEN };
}

function handlePythonError(error, res) {
    console.error(
        "Erreur appel service",
        error.response?.data || error.message
    );

    const status = (
        error.response?.status || 500
    );

    const receivedData = (
        error.response?.data
    );

    let message = (
        "Impossible de contacter le service"
    );

    if (
        typeof receivedData?.error === "string"
    ) {
        message = receivedData.error;
    } else if (
        typeof receivedData?.error?.message === "string"
    ) {
        message = receivedData.error.message;
    } else if (
        typeof receivedData?.detail === "string"
    ) {
        message = receivedData.detail;
    } else if (
        typeof error.message === "string"
    ) {
        message = error.message;
    }

    return res.status(status).json({
        success: false,
        error: {
            message,
        },
    });
}
app.get("/health", (req, res) => {
    res.status(200).json({ success: true, message: "Welcome to energIA API Gateway!" });
});

app.get("/health-ms", async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API_URL}/health`);
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/health-ms-2", async (req, res) => {
    try {
        const response = await axios.get(`${PYTHON_API_URL_2}/health`);
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/plants", async (req, res) => {
    try {
        console.log(`[GET] /plants -> ${PYTHON_API_URL}/plants`);
        const response = await axios.get(`${PYTHON_API_URL}/plants`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/regions", async (req, res) => {
    try {
        console.log(`[GET] /regions -> ${PYTHON_API_URL}/regions`);
        const response = await axios.get(`${PYTHON_API_URL}/regions`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/network", async (req, res) => {
    try {
        console.log(`[GET] /network -> ${PYTHON_API_URL}/network`);
        const response = await axios.get(`${PYTHON_API_URL}/network`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.post("/simulate", async (req, res) => {
    try {
        console.log(`[POST] /simulate -> ${PYTHON_API_URL}/simulate`, req.body);
        const response = await axios.post(`${PYTHON_API_URL}/simulate`, req.body, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/phase1/plants", async (req, res) => {
    try {
        console.log(`[GET] /plants -> ${PYTHON_API_URL_2}/phase1/plants`);
        const response = await axios.get(`${PYTHON_API_URL_2}/phase1/plants`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/phase1/consumption", async (req, res) => {
    try {
        console.log(`[GET] /regions -> ${PYTHON_API_URL_2}/phase1/consumption`);
        const response = await axios.get(`${PYTHON_API_URL_2}/phase1/consumption`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/phase1/simulate-day", async (req, res) => {
    try {
        console.log(`[GET] /regions -> ${PYTHON_API_URL_2}/phase1/simulate-day`);
        const response = await axios.get(`${PYTHON_API_URL_2}/phase1/simulate-day`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/phase2/simulate-day", async (req, res) => {
    try {
        console.log(`[GET] /regions -> ${PYTHON_API_URL_2}/phase2/simulate-day`);
        const response = await axios.get(`${PYTHON_API_URL_2}/phase2/simulate-day`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.get("/phase3/simulate-day", async (req, res) => {
    try {
        console.log(`[GET] /regions -> ${PYTHON_API_URL_2}/phase3/simulate-day`);
        const response = await axios.get(`${PYTHON_API_URL_2}/phase3/simulate-day`, { headers: pythonHeaders() });
        return res.status(200).json({ success: true, response: response.data });
    } catch (error) {
        return handlePythonError(error, res);
    }
});

app.post("/assistant", async (req, res) => {
    try {
        const question = req.body?.question?.trim();

        if (!question) {
            return res.status(400).json({
                success: false,
                error: {
                    message: "La question est obligatoire",
                },
            });
        }

        console.log(
            `[POST] /assistant`,
            { question }
        );

        const response = await axios.post(
            `${PYTHON_MCP_URL}/assistant`,
            { question },
            {
                headers: pythonHeaders(),
                timeout: 180000,
            }
        );

        return res.status(200).json({
            success: true,
            response: response.data,
        });

    } catch (error) {
        return handlePythonError(
            error,
            res
        );
    }
});

app.listen(port, () => {
    console.log(`Gateway service listening at http://energia-gateway:${port}`);
});