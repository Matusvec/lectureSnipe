require "net/http"
require "json"
require "uri"

class LecturesController < ApplicationController
  BACKEND_URL = ENV.fetch("BACKEND_URL", "http://localhost:5000")

  def index
  end

  def process_lecture
    payload = {
      url: params[:panopto_url],
      username: params[:username].presence,
      password: params[:password].presence,
      format: params[:format] || "markdown",
      include_students: params[:include_students] == "1",
      include_timestamps: params[:include_timestamps] == "1",
      download_slides: params[:download_slides] == "1"
    }

    response = post_to_backend("/api/process", payload)

    if response && response["success"]
      @success = true
      @stats = response["stats"]
      @session_id = response["session_id"]
      @notes_path = response["notes_path"]
    else
      @success = false
      @error = response ? response["error"] : "Could not connect to backend server"
    end

    render :result
  rescue StandardError => e
    @success = false
    @error = "Connection error: #{e.message}"
    render :result
  end

  def summary
    payload = {
      url: params[:panopto_url],
      username: params[:username].presence,
      password: params[:password].presence,
      summary_type: params[:summary_type] || "brief",
      include_students: params[:include_students] == "1"
    }

    response = post_to_backend("/api/summary", payload)

    if response && response["success"]
      @success = true
      @summary_text = response["summary"]
    else
      @success = false
      @error = response ? response["error"] : "Could not connect to backend server"
    end

    render :result
  rescue StandardError => e
    @success = false
    @error = "Connection error: #{e.message}"
    render :result
  end

  private

  def post_to_backend(path, payload)
    uri = URI.parse("#{BACKEND_URL}#{path}")
    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = uri.scheme == "https"
    http.open_timeout = 10
    http.read_timeout = 120

    request = Net::HTTP::Post.new(uri.path)
    request["Content-Type"] = "application/json"
    request.body = payload.to_json

    response = http.request(request)
    JSON.parse(response.body)
  rescue StandardError => e
    Rails.logger.error("Backend request failed: #{e.message}")
    nil
  end
end
